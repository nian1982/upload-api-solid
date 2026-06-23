from typing import BinaryIO, Callable, Optional, Protocol

from solid.upload.models import UploadResult


class IUploadService(Protocol):
    def upload_file(
        self,
        file_name: str,
        file_obj: BinaryIO,
        tipo_archivo: str,
        fecha: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        total_bytes: int = 0,
    ) -> UploadResult: ...

    def validate_upload_request(
        self,
        file_name: str,
        tipo_archivo: str,
        fecha: str,
        file_obj: BinaryIO | None = None,
    ) -> tuple[str, str, str]: ...
