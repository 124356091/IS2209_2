import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost:5432/deployhub")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "300"))
