import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    APP_NAME: str = "Global Buyer Acquisition Engine"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"

    # Database
    DATABASE_URL: str = "sqlite:///./impex_leads.db"

    # Security
    SECRET_KEY: str = "development-secret-key-replace-in-prod"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # AI Configuration
    AI_PROVIDER: str = "gemini"  # "gemini" | "openai" | "mock"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gemini-1.5-pro"

    # Email
    SMTP_HOST: str = "smtp.hostinger.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "Indian Export Corp"
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_SSL: bool = True

    # Rate Limiting & Safety
    DAILY_SEND_LIMIT: int = 50
    HOURLY_SEND_LIMIT: int = 10
    DEFAULT_OUTREACH_MODE: str = "assisted"  # "assisted" (Mode A) | "automated" (Mode B)
    ENABLE_AUTO_FOLLOWUPS: bool = False

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
