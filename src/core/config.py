from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ALGORITHM = "HS256"


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    JWT_SECRET_KEY: str

    ACCESS_TOKEN_EXPIRES_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRES_DAYS: int = 7
    INVITE_TOKEN_EXPIRES_HOURS: int = 24
    ACTIVATION_CODE_EXPIRES_MINUTES: int = 15
    RESET_PASSWORD_EXPIRES_MINUTES: int = 15

    ENVIRONMENT: str = "development"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    RESEND_API_KEY: str
    MAIL_FROM: str = "onboarding@resend.dev"
    MAIL_FROM_NAME: str = "Library Management System"

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("DB_PORT")
    @classmethod
    def validate_db_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError(f"DB_PORT must be between 1 and 65535, got {v}")
        return v

    @field_validator("REDIS_PORT")
    @classmethod
    def validate_redis_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError(f"REDIS_PORT must be between 1 and 65535, got {v}")
        return v

    @field_validator("DB_HOST", "REDIS_HOST")
    @classmethod
    def validate_host_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Host cannot be empty or whitespace")
        return v

    @field_validator("DB_NAME", "DB_USER")
    @classmethod
    def validate_db_identifiers(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Database name and user cannot be empty")
        return v

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "production", "test"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}, got '{v}'")
        return v

    @field_validator("ACCESS_TOKEN_EXPIRES_MINUTES")
    @classmethod
    def validate_access_token_expiry(cls, v: int) -> int:
        if v < 1:
            raise ValueError("ACCESS_TOKEN_EXPIRES_MINUTES must be at least 1")
        if v > 1440:
            raise ValueError(
                "ACCESS_TOKEN_EXPIRES_MINUTES should not exceed 900 (15 minutes)"
            )
        return v

    @field_validator("REFRESH_TOKEN_EXPIRES_DAYS")
    @classmethod
    def validate_refresh_token_expiry(cls, v: int) -> int:
        if v < 1:
            raise ValueError("REFRESH_TOKEN_EXPIRES_DAYS must be at least 1")
        if v > 90:
            raise ValueError("REFRESH_TOKEN_EXPIRES_DAYS should not exceed 90")
        return v

    @model_validator(mode="after")
    def validate_db_password_in_production(self) -> "Settings":
        if self.ENVIRONMENT == "production" and not self.DB_PASSWORD:
            raise ValueError("DB_PASSWORD cannot be empty in production")
        if self.ENVIRONMENT == "production" and self.DB_HOST in (
            "localhost",
            "127.0.0.1",
        ):
            raise ValueError("DB_HOST is set to localhost in production")
        return self

    @property
    def DB_URL(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def cookie_secure(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def APP_URL(self) -> str:
        if self.ENVIRONMENT == "production":
            return "https://lms.com"
        return "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
