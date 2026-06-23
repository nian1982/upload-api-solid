from .logger import log


class SFTPError(Exception):
    def __init__(self, message: str, original: Exception | None = None):
        self.message = message
        self.original = original
        log().error("%s: %s", self.__class__.__name__, message)
        super().__init__(message)


class SFTPConnectionError(SFTPError):
    pass


class SFTPTransferError(SFTPError):
    pass


class SFTPDirectoryError(SFTPError):
    pass
