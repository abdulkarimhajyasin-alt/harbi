from functools import lru_cache
from os import getenv

from dotenv import load_dotenv


load_dotenv()


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


class Settings:
    app_name: str = getenv("APP_NAME", "جرد حساباتي")
    database_url: str = normalize_database_url(
        getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/harbi")
    )
    session_secret_key: str = getenv("SESSION_SECRET_KEY", "")

    def __init__(self) -> None:
        if not self.session_secret_key:
            raise RuntimeError("SESSION_SECRET_KEY is required")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
