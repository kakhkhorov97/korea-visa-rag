"""Load raw source documents from data/raw.

Each file is plain text (.txt or .md) with a small metadata header:

    ---
    title: 출입국관리법 시행령
    source_url: https://www.law.go.kr/...
    doc_type: law          # "law" (split by article) or "guide" (split by section)
    retrieved: 2026-10-22
    ---
    (document text...)

Keeping the source URL and date on every document is what lets the assistant
cite its answers later.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Document:
    doc_id: str
    title: str
    text: str
    source_url: str = ""
    doc_type: str = "guide"
    retrieved: str = ""
    extra: dict = field(default_factory=dict)


def parse_document(raw: str, doc_id: str) -> Document:
    meta: dict[str, str] = {}
    body = raw
    stripped = raw.lstrip("﻿")
    if stripped.startswith("---"):
        parts = stripped.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    # A URL fragment is data; only whitespace followed by # starts a comment.
                    meta[key.strip()] = re.split(r"\s+#", value, maxsplit=1)[0].strip()
            body = parts[2]
    known = {"title", "source_url", "doc_type", "retrieved"}
    return Document(
        doc_id=doc_id,
        title=meta.get("title", doc_id),
        text=body.strip(),
        source_url=meta.get("source_url", ""),
        doc_type=meta.get("doc_type", "guide"),
        retrieved=meta.get("retrieved", ""),
        extra={k: v for k, v in meta.items() if k not in known},
    )


def load_documents(raw_dir: Path) -> list[Document]:
    docs = []
    for path in sorted(raw_dir.glob("*")):
        if path.suffix.lower() not in {".txt", ".md"} or path.name.startswith("README"):
            continue
        docs.append(parse_document(path.read_text(encoding="utf-8"), doc_id=path.stem))
    return docs
