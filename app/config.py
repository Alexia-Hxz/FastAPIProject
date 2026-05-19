import os
from pydantic_settings import BaseSettings

# Absolute path to project root, so working directory doesn't matter
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Settings(BaseSettings):
    model_config = {
        "env_file": os.path.join(PROJECT_ROOT, ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    # Application
    APP_NAME: str = "AI-Admin"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    SECRET_KEY: str = "change-me-to-random-string-at-least-32-chars"

    # Database — defaults to SQLite for zero-setup local dev
    # In Docker, set DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME instead
    DATABASE_URL: str = ""
    DB_HOST: str = ""
    DB_PORT: str = "5432"
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_NAME: str = ""

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.DB_HOST:
            return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        db_path = os.path.join(PROJECT_ROOT, "aiadmin.db")
        return f"sqlite+aiosqlite:///{db_path}"

    @property
    def readonly_database_url(self) -> str:
        return self.database_url

    # Redis — optional, graceful degradation when unavailable
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # JWT
    JWT_SECRET_KEY: str = "change-me-jwt-secret-at-least-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI
    AI_ENABLED: bool = True
    AI_PROVIDER: str = "deepseek"
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.deepseek.com/v1"
    AI_MODEL: str = "deepseek-chat"
    AI_MAX_TOKENS: int = 2048
    AI_TEMPERATURE: float = 0.1

    # NL2SQL Safety
    NL2SQL_MAX_RESULT_ROWS: int = 1000
    NL2SQL_QUERY_TIMEOUT_MS: int = 5000

    # AI File Upload
    AI_MAX_IMAGE_SIZE_MB: int = 10

    # File Storage
    FILE_STORAGE_TYPE: str = "local"
    FILE_STORAGE_PATH: str = "./storage"
    FILE_MAX_SIZE_MB: int = 10

    # Rate Limit
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60


settings = Settings()
