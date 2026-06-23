from typing import BinaryIO, Callable, Optional, Protocol

from .logger import log


class ISFTPClient(Protocol):
    def connect(self) -> None: ...

    def disconnect(self) -> None: ...

    def ensure_directory(self, remote_dir: str) -> None: ...

    def upload_file_stream(
        self,
        remote_path: str,
        file_obj: BinaryIO,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        total_bytes: int = 0,
    ) -> int: ...
