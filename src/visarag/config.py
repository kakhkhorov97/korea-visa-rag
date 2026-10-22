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

OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
LAW_API_OC = os.getenv("LAW_API_OC", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Without an OpenAI key the project still runs in free "search-only" mode:
# BM25 keyword search returns the most relevant articles, with no AI-written answer.
HAS_OPENAI = bool(os.getenv("OPENAI_API_KEY"))

# Retrieval settings (tune these during evaluation)
TOP_K = 5                 # chunks handed to the LLM
CANDIDATES_PER_RETRIEVER = 20
RRF_K = 60                # standard constant for Reciprocal Rank Fusion
GUIDE_CHUNK_MAX_CHARS = 800
GUIDE_CHUNK_OVERLAP = 100
