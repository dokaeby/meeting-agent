from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MA_", env_file=".env", extra="ignore")
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://meeting:meeting@localhost:5432/meeting"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "development-only-change-before-production"
    public_url: str = "http://localhost:5173"
    provider_mode: Literal["live", "disabled", "test"] = "disabled"
    storage_path: Path = Path("var/files")
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = False
    mail_from: str = "meetings@example.com"
    groq_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_stt_model: str = "whisper-large-v3-turbo"
    zoom_client_id: str = ""
    zoom_client_secret: str = ""
    zoom_webhook_secret: str = ""
    zoom_transcript_wait_seconds: int = 120
    kakao_client_id: str = ""
    kakao_client_secret: str = ""
    pdf_font: str = ""
    max_upload_bytes: int = 200 * 1024 * 1024
    max_transcript_chars: int = 400_000
    max_audio_seconds: int = 7200

    @model_validator(mode="after")
    def production_guards(self):
        if self.provider_mode == "test" and self.environment != "test":
            raise ValueError("test provider is restricted to test environment")
        if self.environment == "production":
            if len(self.secret_key) < 40 or self.secret_key.startswith("development"):
                raise ValueError("production requires a unique 40+ character secret")
            if not self.database_url.startswith("postgresql"):
                raise ValueError("production requires PostgreSQL")
            if not self.public_url.startswith("https://"):
                raise ValueError("production requires HTTPS")
            if self.provider_mode != "live":
                raise ValueError("production requires live providers")
        return self
