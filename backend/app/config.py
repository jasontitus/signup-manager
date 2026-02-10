from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Security — loaded from .env (dev) or vault (production)
    SECRET_KEY: str = ""
    ENCRYPTION_KEY: str = ""
    EMAIL_BLIND_INDEX_SALT: str = ""

    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 480

    # Database
    DATABASE_URL: str = "sqlite:////app/data/members.db"

    # CORS
    FRONTEND_URL: str = "http://localhost:5173"

    # First Run Admin
    FIRST_RUN_ADMIN_USER: Optional[str] = None
    FIRST_RUN_ADMIN_PASSWORD: Optional[str] = None

    # Vault file path
    VAULT_FILE: str = "/app/data/.vault"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


def load_secrets_from_vault(secrets: dict):
    """Populate settings with secrets decrypted from the vault."""
    for key, value in secrets.items():
        if hasattr(settings, key) and value is not None:
            object.__setattr__(settings, key, value)
