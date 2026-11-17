import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

BASE_URL = os.getenv("LLM_BASE_URL", "").rstrip("/")
API_KEY = os.getenv("LLM_API_KEY", "")
MODEL = os.getenv("LLM_MODEL", "")
REVIEW_MODEL = os.getenv("LLM_REVIEW_MODEL") or MODEL
CHAPTER_WORDS = int(os.getenv("CHAPTER_WORDS", "3000"))
MAX_REVISE_ROUNDS = int(os.getenv("MAX_REVISE_ROUNDS", "2"))
OUTPUT_ROOT = PROJECT_ROOT / "output"


def validate():
    missing = [k for k, v in [("LLM_BASE_URL", BASE_URL), ("LLM_API_KEY", API_KEY), ("LLM_MODEL", MODEL)] if not v]
    if missing:
        raise SystemExit(f"缺少配置: {', '.join(missing)}。请复制 .env.example 为 .env 并填写。")