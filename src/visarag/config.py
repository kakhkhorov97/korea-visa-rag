"""Central settings. Everything configurable lives here so the rest of the code
never reads environment variables directly."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
INDEX_DIR = ROOT / "data" / "index"
CHUNKS_FILE = PROCESSED_DIR / "chunks.jsonl"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-flash-latest")
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
LAW_API_OC = os.getenv("LAW_API_OC", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Without a Gemini key the project still runs in free "search-only" mode:
# BM25 keyword search returns the most relevant articles, with no AI-written answer.
HAS_GEMINI = bool(GEMINI_API_KEY)

# Retrieval settings (tune these during evaluation)
TOP_K = 5                 # chunks handed to the LLM
CANDIDATES_PER_RETRIEVER = 20
RRF_K = 60                # standard constant for Reciprocal Rank Fusion
GUIDE_CHUNK_MAX_CHARS = 800
GUIDE_CHUNK_OVERLAP = 100
