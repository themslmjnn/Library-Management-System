from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    JWT_SECRET_KEY: str
    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRES_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRES_DAYS: int = 7
    
    ENVIRONMENT: str = "development"

    @property
    def DB_URL(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def cookie_secure(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()