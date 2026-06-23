from pydantic_settings import BaseSettings, SettingsConfigDict


class KeycloakSettings(BaseSettings):
    url: str = "http://localhost:8080"
    realm: str = ""
    client_id: str = ""
    verify_audience: bool = False
    jwks_refresh_seconds: int = 3600

    model_config = SettingsConfigDict(
        env_prefix="KEYCLOAK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def issuer(self) -> str:
        return f"{self.url.rstrip('/')}/realms/{self.realm}"

    @property
    def jwks_url(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/certs"
