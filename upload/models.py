from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass(slots=True)
class UploadResult:
    id: UUID
    success: bool
    file_name: str
    extension: str
    size_bytes: int
    size_display: str
    upload_path: str
    upload_time_seconds: float
    tipo_archivo: str
    fecha: str
    uploaded_at: datetime | None = None
    error: str | None = None
    error_code: str | None = None

    @classmethod
    def success_result(
        cls,
        file_name: str,
        extension: str,
        size_bytes: int,
        size_display: str,
        upload_path: str,
        upload_time_seconds: float,
        tipo_archivo: str,
        fecha: str,
    ) -> "UploadResult":
        return cls(
            id=uuid4(),
            success=True,
            file_name=file_name,
            extension=extension,
            size_bytes=size_bytes,
            size_display=size_display,
            upload_path=upload_path,
            upload_time_seconds=upload_time_seconds,
            tipo_archivo=tipo_archivo,
            fecha=fecha,
            uploaded_at=datetime.now(),
        )

    @classmethod
    def error_result(
        cls,
        file_name: str,
        extension: str,
        size_bytes: int,
        size_display: str,
        upload_path: str,
        upload_time_seconds: float,
        tipo_archivo: str,
        fecha: str,
        error: str,
        error_code: str = "UPLOAD_ERROR",
    ) -> "UploadResult":
        return cls(
            id=uuid4(),
            success=False,
            file_name=file_name,
            extension=extension,
            size_bytes=size_bytes,
            size_display=size_display,
            upload_path=upload_path,
            upload_time_seconds=upload_time_seconds,
            tipo_archivo=tipo_archivo,
            fecha=fecha,
            error=error,
            error_code=error_code,
        )

    @classmethod
    def file_not_found(cls, file_name: str) -> "UploadResult":
        return cls(
            id=uuid4(),
            success=False,
            file_name=file_name,
            extension="",
            size_bytes=0,
            size_display="0.00 B",
            upload_path="",
            upload_time_seconds=0.0,
            tipo_archivo="",
            fecha="",
            error=f"File not found: {file_name}",
        )
