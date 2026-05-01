from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "HiSMap"
    API_V1_PREFIX: str = "/api"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://hismap:hismap@localhost:5432/hismap"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://hismap:hismap@localhost:5432/hismap"

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {"env_prefix": "HISMAP_", "env_file": ".env"}


settings = Settings()
