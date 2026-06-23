from pydantic_settings import BaseSettings, SettingsConfigDict


class UploadSettings(BaseSettings):
    allowed_file_types: str = "REPOSITORIO"
    allowed_extensions: str = ".xlsx,.xls,.csv,.pdf"
    max_upload_size_mb: int = 500
    environment: str = "development"
    upload_dir: str = "/upload"

    model_config = SettingsConfigDict(
        env_prefix="SFTP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_file_types_list(self) -> list[str]:
        return [t.strip().upper() for t in self.allowed_file_types.split(",") if t.strip()]

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [e.strip().lower() for e in self.allowed_extensions.split(",") if e.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024
