from dataclasses import dataclass
from datetime import datetime

from .logger import log


@dataclass(slots=True)
class SFTPResult:
    success: bool
    bytes_transferred: int
    remote_path: str
    elapsed_seconds: float
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
