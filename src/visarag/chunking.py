"""Split documents into retrievable chunks.

Why not just cut every N characters?
Korean laws are organised as 조 (article) > 항 (paragraph) > 호 (item).
A fixed-size cut can split one rule in half, so the retriever finds half a
rule and the LLM answers wrongly. Instead:

* law documents   -> one chunk per article (제N조 / 제N조의M)
* guide documents -> one chunk per section heading, with long sections
                     split by paragraph into ~800-character windows

Every chunk carries its title, article label and source URL for citations.
"""

import re
from dataclasses import asdict, dataclass

from .config import GUIDE_CHUNK_MAX_CHARS, GUIDE_CHUNK_OVERLAP
from .documents import Document

# Matches an article header at the start of a line, e.g.
#   제12조(외국인의 체류자격)   /   제23조의2 (취업활동)
ARTICLE_RE = re.compile(r"(?m)^\s*(제\s*\d+\s*조(?:\s*의\s*\d+)?)\s*(?:\(([^)\n]*)\))?")

# Section headings found in government guides: markdown "#", ■ □ ○ ▶ bullets,
# or numbered headings like "1." / "가."
HEADING_RE = re.compile(r"(?m)^\s*(#{1,4}\s+.+|[■□▶◆●]\s*.+|\d{1,2}\.\s+\S.{0,60}|[가-하]\.\s+\S.{0,60})$")


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    section: str          # e.g. "제12조(체류자격)" or a guide heading
    text: str
    source_url: str
    retrieved: str

    def citation(self) -> str:
        return f"{self.title} {self.section}".strip()

    def to_dict(self) -> dict:
        return asdict(self)


def _normalise_label(label: str) -> str:
    return re.sub(r"\s+", "", label)


def chunk_law(doc: Document) -> list[Chunk]:
    matches = list(ARTICLE_RE.finditer(doc.text))
    if not matches:
        # Reviewed annex rows are complete units; numbered table cells are not headings.
        if doc.extra.get("excerpt"):
            return [_make(doc, 0, "", doc.text)]
        return chunk_guide(doc)

    chunks: list[Chunk] = []
    preamble = doc.text[: matches[0].start()].strip()
    if len(preamble) > 50:
        chunks.append(_make(doc, 0, "전문", preamble))

    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(doc.text)
        body = doc.text[m.start():end].strip()
        label = _normalise_label(m.group(1))
        if m.group(2):
            label += f"({m.group(2).strip()})"
        # Very long articles (e.g. tables of visa types) are windowed but keep the label.
        for j, piece in enumerate(_window(body, GUIDE_CHUNK_MAX_CHARS * 3, GUIDE_CHUNK_OVERLAP)):
            section = label if j == 0 else f"{label} (계속 {j + 1})"
            chunks.append(_make(doc, len(chunks), section, piece))
    return chunks


def chunk_guide(doc: Document) -> list[Chunk]:
    heads = list(HEADING_RE.finditer(doc.text))
    sections: list[tuple[str, str]] = []
    if not heads:
        sections.append(("", doc.text))
    else:
        if doc.text[: heads[0].start()].strip():
            sections.append(("", doc.text[: heads[0].start()]))
        for i, h in enumerate(heads):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(doc.text)
            heading = h.group(1).strip().lstrip("#■□▶◆● ").strip()
            sections.append((heading, doc.text[h.start():end]))

    chunks: list[Chunk] = []
    for heading, body in sections:
        body = body.strip()
        if not body:
            continue
        for piece in _window(body, GUIDE_CHUNK_MAX_CHARS, GUIDE_CHUNK_OVERLAP):
            chunks.append(_make(doc, len(chunks), heading, piece))
    return chunks


def chunk_document(doc: Document) -> list[Chunk]:
    return chunk_law(doc) if doc.doc_type == "law" else chunk_guide(doc)


def _window(text: str, max_chars: int, overlap: int) -> list[str]:
    """Split on paragraph boundaries into windows of at most ~max_chars."""
    if len(text) <= max_chars:
        return [text]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n|\n(?=\s*[①-⑳])", text) if p.strip()]
    windows, current = [], ""
    for p in paragraphs:
        while len(p) > max_chars:                 # a single huge paragraph
            if current:
                windows.append(current)
                current = ""
            windows.append(p[:max_chars])
            p = p[max_chars - overlap:]
        if current and len(current) + len(p) + 1 > max_chars:
            windows.append(current)
            tail = current[-overlap:] if overlap else ""
            current = (tail + "\n" + p).strip()
        else:
            current = (current + "\n" + p).strip()
    if current:
        windows.append(current)
    return windows


def _make(doc: Document, idx: int, section: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=f"{doc.doc_id}::{idx:04d}",
        doc_id=doc.doc_id,
        title=doc.title,
        section=section,
        text=text,
        source_url=doc.source_url,
        retrieved=doc.retrieved,
    )
