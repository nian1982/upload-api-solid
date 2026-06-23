import os
import time
from typing import BinaryIO, Callable, Optional
from datetime import datetime

from sftp.exceptions import SFTPConnectionError, SFTPDirectoryError, SFTPTransferError
from sftp.interface import ISFTPClient
from shared.logger import log
from upload.config import UploadSettings
from upload.exceptions import (
    ExtensionNotAllowedError,
    FileContentMismatchError,
    FileTooLargeError,
    FileTypeNotAllowedError,
    InvalidDateError,
)
from upload.models import UploadResult

logger = log("solid.upload")

MAGIC_BYTE_CHECKS: dict[str, list[tuple[bytes, int]]] = {
    ".pdf": [(b"%PDF", 0)],
    ".xlsx": [(b"PK\x03\x04", 0)],
    ".xls": [(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1", 0)],
}


class UploadService:
    def __init__(
        self,
        sftp_client: ISFTPClient,
        settings: UploadSettings | None = None,
        upload_dir: str | None = None,
    ):
        self._sftp = sftp_client
        self._settings = settings or UploadSettings()
        self._upload_dir = upload_dir or self._settings.upload_dir

    def upload_file(
        self,
        file_name: str,
        file_obj: BinaryIO,
        tipo_archivo: str,
        fecha: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        total_bytes: int = 0,
    ) -> UploadResult:
        tipo_archivo = tipo_archivo.strip().upper()
        self._validate_file_type(tipo_archivo)
        self._validate_fecha(fecha)

        extension = self._get_extension(file_name)
        self._validate_extension(extension)
        self._validate_magic_bytes(file_obj, extension)
        self._validate_file_size(file_obj)

        date_compressed = fecha.replace("-", "")
        hour = datetime.now().strftime("%H")
        remote_dir = f"{self._upload_dir.rstrip('/')}/{tipo_archivo}/{date_compressed}/{hour}"
        remote_path = f"{remote_dir}/{file_name}"

        logger.info(
            "Starting upload: type=%s, date=%s, file=%s",
            tipo_archivo, fecha, file_name,
        )

        start = time.perf_counter()
        bytes_sent = 0
        try:
            self._sftp.connect()
            self._sftp.ensure_directory(remote_dir)
            bytes_sent = self._sftp.upload_file_stream(
                remote_path, file_obj,
                progress_callback=progress_callback,
                total_bytes=total_bytes or 0,
            )
            elapsed = time.perf_counter() - start
            logger.info(
                "Upload successful: %s (%d bytes) in %.2fs",
                remote_path, bytes_sent, elapsed,
            )
            return UploadResult.success_result(
                file_name=file_name,
                extension=extension,
                size_bytes=bytes_sent,
                size_display=self._format_size(bytes_sent),
                upload_path=remote_path,
                upload_time_seconds=round(elapsed, 2),
                tipo_archivo=tipo_archivo,
                fecha=fecha,
            )
        except SFTPConnectionError as e:
            elapsed = time.perf_counter() - start
            logger.error("SFTP connection failed: %s", e)
            return UploadResult.error_result(
                file_name=file_name,
                extension=extension,
                size_bytes=bytes_sent,
                size_display=self._format_size(bytes_sent),
                upload_path=remote_path,
                upload_time_seconds=round(elapsed, 2),
                tipo_archivo=tipo_archivo,
                fecha=fecha,
                error=f"No se pudo conectar al servidor SFTP ({self._sftp._settings.host}:{self._sftp._settings.port})",
                error_code="SFTP_CONNECTION_ERROR",
            )
        except SFTPDirectoryError as e:
            elapsed = time.perf_counter() - start
            logger.error("SFTP directory error: %s", e)
            return UploadResult.error_result(
                file_name=file_name,
                extension=extension,
                size_bytes=bytes_sent,
                size_display=self._format_size(bytes_sent),
                upload_path=remote_path,
                upload_time_seconds=round(elapsed, 2),
                tipo_archivo=tipo_archivo,
                fecha=fecha,
                error=str(e),
                error_code="SFTP_DIRECTORY_ERROR",
            )
        except SFTPTransferError as e:
            elapsed = time.perf_counter() - start
            logger.error("SFTP transfer error: %s", e)
            return UploadResult.error_result(
                file_name=file_name,
                extension=extension,
                size_bytes=bytes_sent,
                size_display=self._format_size(bytes_sent),
                upload_path=remote_path,
                upload_time_seconds=round(elapsed, 2),
                tipo_archivo=tipo_archivo,
                fecha=fecha,
                error=str(e),
                error_code="SFTP_TRANSFER_ERROR",
            )
        except Exception as e:
            elapsed = time.perf_counter() - start
            logger.error("Upload failed: %s - %s", file_name, e)
            return UploadResult.error_result(
                file_name=file_name,
                extension=extension,
                size_bytes=bytes_sent,
                size_display=self._format_size(bytes_sent),
                upload_path=remote_path,
                upload_time_seconds=round(elapsed, 2),
                tipo_archivo=tipo_archivo,
                fecha=fecha,
                error=self._safe_error(e),
                error_code="UPLOAD_ERROR",
            )
        finally:
            self._sftp.disconnect()

    def validate_upload_request(
        self,
        file_name: str,
        tipo_archivo: str,
        fecha: str,
        file_obj: BinaryIO | None = None,
    ) -> tuple[str, str, str]:
        tipo_archivo = tipo_archivo.strip().upper()
        self._validate_file_type(tipo_archivo)
        self._validate_fecha(fecha)
        extension = self._get_extension(file_name)
        self._validate_extension(extension)
        if file_obj:
            self._validate_magic_bytes(file_obj, extension)
            self._validate_file_size(file_obj)
        return tipo_archivo, extension, fecha

    def _safe_error(self, error: Exception) -> str:
        if self._settings.environment.lower() == "production":
            return "An internal error occurred. Contact the administrator."
        return str(error)

    def _validate_extension(self, extension: str) -> None:
        allowed = self._settings.allowed_extensions_list
        if extension not in allowed:
            raise ExtensionNotAllowedError(extension, allowed)

    def _validate_magic_bytes(self, file_obj: BinaryIO, extension: str) -> None:
        checks = MAGIC_BYTE_CHECKS.get(extension)
        if not checks:
            return
        pos = file_obj.tell()
        try:
            header = file_obj.read(16)
            file_obj.seek(pos)
            for magic, offset in checks:
                if not header[offset:].startswith(magic):
                    raise FileContentMismatchError(extension)
        except (OSError, AttributeError):
            pass

    def _validate_file_size(self, file_obj: BinaryIO) -> None:
        max_bytes = self._settings.max_upload_size_bytes
        if max_bytes <= 0:
            return
        try:
            pos = file_obj.tell()
            file_obj.seek(0, os.SEEK_END)
            size = file_obj.tell()
            file_obj.seek(pos)
            if size > max_bytes:
                raise FileTooLargeError(self._settings.max_upload_size_mb)
        except (OSError, AttributeError):
            pass

    def _validate_file_type(self, tipo_archivo: str) -> None:
        allowed = self._settings.allowed_file_types_list
        if tipo_archivo not in allowed:
            raise FileTypeNotAllowedError(tipo_archivo, allowed)

    def _validate_fecha(self, fecha: str) -> None:
        try:
            datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            raise InvalidDateError(fecha)

    def _get_extension(self, file_name: str) -> str:
        idx = file_name.rfind(".")
        return file_name[idx:].lower() if idx != -1 else ""

    @staticmethod
    def _format_size(bytes_: int) -> str:
        size = float(bytes_)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"
