from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR.parent / ".env")
DATA_DIR = Path(os.getenv("SQ_DATA_DIR", BASE_DIR / "data")).expanduser().resolve()
UPLOAD_DIR = Path(os.getenv("SQ_UPLOAD_DIR", DATA_DIR / "uploads")).expanduser().resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'semester_quest.db').as_posix()}")
SECRET_KEY = os.getenv("SQ_SECRET_KEY", "dev-only-change-this-secret-before-deploying")
ACCESS_TOKEN_MINUTES = int(os.getenv("SQ_ACCESS_TOKEN_MINUTES", "10080"))
OTP_MINUTES = int(os.getenv("SQ_OTP_MINUTES", "10"))
DEV_SHOW_CODE = os.getenv("DEV_SHOW_CODE", "1").lower() in {"1", "true", "yes"}
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
MAX_UPLOAD_MB = int(os.getenv("SQ_MAX_UPLOAD_MB", "20"))
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
