from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ProgressType(str, Enum):
    STARTING = "starting"
    PROGRESS = "progress"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ProgressEvent:
    type: ProgressType
    task_id: str
    file_name: str | None = None
    total_bytes: int | None = None
    size_display: str | None = None
    username: str | None = None
    percentage: float | None = None
    bytes_sent: int | None = None
    speed_mbps: float | None = None
    eta_seconds: int | None = None
    elapsed: float | None = None
    result: dict | None = None
    message: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}
