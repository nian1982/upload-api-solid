class UploadError(Exception):
    def __init__(self, message: str, code: str = "UPLOAD_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class FileTypeNotAllowedError(UploadError):
    def __init__(self, file_type: str, allowed: list[str]):
        super().__init__(
            message=f"File type '{file_type}' not allowed. Allowed: {', '.join(allowed)}",
            code="FILE_TYPE_NOT_ALLOWED",
        )


class ExtensionNotAllowedError(UploadError):
    def __init__(self, extension: str, allowed: list[str]):
        super().__init__(
            message=f"Extension '{extension}' not allowed. Allowed: {', '.join(allowed)}",
            code="EXTENSION_NOT_ALLOWED",
        )


class InvalidDateError(UploadError):
    def __init__(self, date_str: str):
        super().__init__(
            message=f"Invalid date format '{date_str}'. Expected YYYY-MM-DD",
            code="INVALID_DATE",
        )


class FileTooLargeError(UploadError):
    def __init__(self, max_size_mb: int):
        super().__init__(
            message=f"File exceeds maximum size of {max_size_mb}MB",
            code="FILE_TOO_LARGE",
        )


class FileContentMismatchError(UploadError):
    def __init__(self, extension: str):
        super().__init__(
            message=f"File content does not match extension '{extension}'",
            code="FILE_CONTENT_MISMATCH",
        )
