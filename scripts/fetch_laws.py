"""Download Korean immigration laws from the official law Open API (open.law.go.kr)
and save them into data/raw/ in the format documents.py expects.

Setup (free):
  1. Sign up at https://open.law.go.kr and apply for Open API use.
  2. Your "OC" value is the ID part of your registered email (before the @).
  3. Put it in .env as LAW_API_OC=yourid

Run:
  python scripts/fetch_laws.py

Note: the API's JSON field names are Korean (e.g. "조문내용"). If the API
changes, print the raw JSON once and adjust `article_lines()` below.
"""

import sys
from datetime import date
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from visarag.config import LAW_API_OC, RAW_DIR  # noqa: E402

SEARCH_URL = "https://www.law.go.kr/DRF/lawSearch.do"
SERVICE_URL = "https://www.law.go.kr/DRF/lawService.do"

# The laws that define visa (체류자격) rules. Add more as you expand scope.
LAWS = {
    "immigration_act": "출입국관리법",
    "immigration_act_decree": "출입국관리법 시행령",
    "immigration_act_rules": "출입국관리법 시행규칙",
}


def as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def find_law(name: str) -> dict:
    params = {"OC": LAW_API_OC, "target": "law", "type": "JSON", "query": name}
    data = requests.get(SEARCH_URL, params=params, timeout=30).json()
    results = as_list(data.get("LawSearch", {}).get("law"))
    exact = [r for r in results if r.get("법령명한글") == name]
    if not (exact or results):
        raise RuntimeError(f"No law found for {name!r}. Raw response: {str(data)[:300]}")
    return (exact or results)[0]


def article_lines(article: dict) -> list[str]:
    """Flatten one 조문단위 (article) with its 항 (paragraphs) and 호 (items)."""
    lines = [str(article.get("조문내용", "")).strip()]
    for para in as_list(article.get("항")):
        if isinstance(para, dict):
            if para.get("항내용"):
                lines.append(str(para["항내용"]).strip())
            for item in as_list(para.get("호")):
                if isinstance(item, dict) and item.get("호내용"):
                    lines.append("  " + str(item["호내용"]).strip())
    return [line for line in lines if line]


def fetch_law_text(mst: str) -> str:
    params = {"OC": LAW_API_OC, "target": "law", "type": "JSON", "MST": mst}
    data = requests.get(SERVICE_URL, params=params, timeout=60).json()
    articles = as_list(data.get("법령", {}).get("조문", {}).get("조문단위"))
    blocks = []
    for art in articles:
        if art.get("조문여부") == "전문":      # chapter headings, not articles
            continue
        blocks.append("\n".join(article_lines(art)))
    return "\n\n".join(blocks)


def main() -> None:
    if not LAW_API_OC:
        sys.exit("Set LAW_API_OC in .env first (see the top of this file).")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for slug, name in LAWS.items():
        info = find_law(name)
        mst = info.get("법령일련번호")
        text = fetch_law_text(mst)
        url = f"https://www.law.go.kr/법령/{name.replace(' ', '')}"
        header = (
            f"---\ntitle: {name}\nsource_url: {url}\ndoc_type: law\n"
            f"retrieved: {date.today().isoformat()}\nmst: {mst}\n---\n\n"
        )
        out = RAW_DIR / f"{slug}.txt"
        out.write_text(header + text, encoding="utf-8")
        print(f"Saved {name}: {len(text):,} chars -> {out.relative_to(RAW_DIR.parents[1])}")


if __name__ == "__main__":
    main()
