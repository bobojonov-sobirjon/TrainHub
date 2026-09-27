from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "TrainHub"
    app_env: str = "local"
    app_debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8009

    database_url: str = "postgresql://postgres:0576@127.0.0.1:5432/trainhub_db"
    database_ssl: bool = False
    redis_url: str = "redis://127.0.0.1:6379/0"

    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 14

    # local | s3  — hozir S3 yo‘q, default local folder
    storage_backend: str = "local"
    media_dir: str = "media"
    public_base_url: str = "http://127.0.0.1:8009"

    s3_endpoint: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = ""
    s3_region: str = "us-east-1"

    app_origins: str = "http://localhost:3000"
    admin_origins: str = "http://localhost:5173"

    seed_admin_email: str = "admin@trainhub.local"
    seed_admin_password: str = "ChangeMeAdmin1"

    google_client_ids: str = ""
    apple_bundle_ids: str = ""
    firebase_type: str = "service_account"
    firebase_project_id: str = ""
    firebase_private_key_id: str = ""
    firebase_private_key: str = ""
    firebase_client_email: str = ""
    firebase_client_id: str = ""
    firebase_auth_uri: str = "https://accounts.google.com/o/oauth2/auth"
    firebase_token_uri: str = "https://oauth2.googleapis.com/token"
    firebase_auth_provider_x509_cert_url: str = "https://www.googleapis.com/oauth2/v1/certs"
    firebase_client_x509_cert_url: str = ""
    firebase_universe_domain: str = "googleapis.com"
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    telegram_webhook_secret: str = ""
    telegram_gateway_token: str = ""
    sms_eskiz_email: str = ""
    sms_eskiz_password: str = ""
    sms_eskiz_from: str = "4546"

    @property
    def google_audiences(self) -> list[str]:
        return [item.strip() for item in self.google_client_ids.split(",") if item.strip()]

    @property
    def apple_audiences(self) -> list[str]:
        return [item.strip() for item in self.apple_bundle_ids.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origins(self) -> list[str]:
        raw = f"{self.app_origins},{self.admin_origins}"
        return [item.strip() for item in raw.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
