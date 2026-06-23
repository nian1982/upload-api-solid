import os
import sys
import time
from typing import Callable, Optional

from sftp.paramiko_client import ParamikoSFTPClient
from upload.models import UploadResult
from upload.service import UploadService


def _make_progress_bar(total_bytes: int) -> Callable[[int, int], None]:
    start = time.perf_counter()

    def progress(sent: int, _total: int) -> None:
        elapsed = time.perf_counter() - start
        pct = sent / total_bytes * 100
        speed = sent / elapsed / 1_000_000 if elapsed > 0 else 0
        bar = "█" * int(30 * sent / total_bytes) + "░" * (30 - int(30 * sent / total_bytes))
        print(f"\r  {bar} {pct:5.1f}%  {sent/1_000_000:.2f}MB  {speed:.2f}MB/s",
              end="", file=sys.stderr, flush=True)

    return progress


def upload_file(
        file_path: str,
        tipo_archivo: str,
        fecha: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        show_progress: bool = False,
    ) -> UploadResult:
    
    if not os.path.isfile(file_path):
        return UploadResult.file_not_found(file_path)

    sftp = ParamikoSFTPClient()
    service = UploadService(sftp)

    file_name = os.path.basename(file_path)
    total_bytes = os.path.getsize(file_path)

    cb = progress_callback
    if show_progress and cb is None:
        cb = _make_progress_bar(total_bytes)

    try:
        with open(file_path, "rb") as f:
            result = service.upload_file(
                file_name, f, tipo_archivo, fecha,
                progress_callback=cb, total_bytes=total_bytes,
            )
    finally:
        if show_progress and cb is not None:
            print(file=sys.stderr)

    return result
