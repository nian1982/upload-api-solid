from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .logger import log


class SFTPSettings(BaseSettings):
    host: str = "localhost"
    port: int = 22
    user: str = Field(default="")
    password: str = Field(default="", validation_alias="SFTP_PASS")
    upload_dir: str = "/upload"
    chunk_size: int = 16777216
    window_size: int = 64 * 1024 * 1024
    timeout_seconds: int = 30

    model_config = SettingsConfigDict(
        env_prefix="SFTP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def model_post_init(self, __context):
        log().info(
            "SFTPSettings loaded: host=%s, port=%d, user=%s, upload_dir=%s",
            self.host, self.port, self.user, self.upload_dir,
        )
