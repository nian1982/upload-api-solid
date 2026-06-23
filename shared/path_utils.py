from datetime import datetime


def build_upload_path(
    upload_dir: str,
    tipo_archivo: str,
    fecha: str,
    file_name: str,
) -> str:
    date_compressed = fecha.replace("-", "")
    hour = datetime.now().strftime("%H")
    return f"{upload_dir.rstrip('/')}/{tipo_archivo}/{date_compressed}/{hour}/{file_name}"
