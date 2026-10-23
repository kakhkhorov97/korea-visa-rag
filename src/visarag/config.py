"""Central settings. Everything configurable lives here so the rest of the code
never reads environment variables directly."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATA_DIR = Path(os.getenv("VISARAG_DATA_DIR", str(ROOT / "data")))
RAW_DIR = Path(os.getenv("VISARAG_RAW_DIR", str(ROOT / "data" / "raw")))
PROCESSED_DIR = DATA_DIR / "processed"
INDEX_DIR = DATA_DIR / "index"
CHUNKS_FILE = PROCESSED_DIR / "chunks.jsonl"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-3.5-flash-lite")
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
LAW_API_OC = os.getenv("LAW_API_OC", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Without a Gemini key, or when explicitly requested, use free "search-only" mode:
# BM25 keyword search returns the most relevant articles, with no AI-written answer.
SEARCH_ONLY = os.getenv("SEARCH_ONLY", "false").strip().lower() in {"true", "1", "yes"}
HAS_GEMINI = bool(GEMINI_API_KEY) and not SEARCH_ONLY

# Retrieval settings (tune these during evaluation)
TOP_K = 5                 # chunks handed to the LLM
CANDIDATES_PER_RETRIEVER = 20
RRF_K = 60                # standard constant for Reciprocal Rank Fusion
GUIDE_CHUNK_MAX_CHARS = 800
GUIDE_CHUNK_OVERLAP = 100

# Public API limits apply per process/instance; the daily budget persists on disk.
API_REQUESTS_PER_MINUTE = int(os.getenv("API_REQUESTS_PER_MINUTE", "20"))
API_DAILY_AI_REQUESTS = int(os.getenv("API_DAILY_AI_REQUESTS", "100"))
API_MAX_CONCURRENT_AI = int(os.getenv("API_MAX_CONCURRENT_AI", "2"))
