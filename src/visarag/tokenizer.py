"""Korean tokenizer for keyword (BM25) search.

Korean attaches particles to words: "비자를", "비자는", "비자의" are all "비자".
Splitting on spaces would treat them as different words, so BM25 would miss
matches. Kiwi (a Korean morphological analyzer) splits words into morphemes
and we keep only the meaningful ones (nouns, verb/adjective stems, foreign
words, numbers).

Visa codes like "D-10" or "E-7-1" are pulled out first as single tokens,
because they are the most important keywords in this domain and a generic
tokenizer would break them into "D", "-", "10".
"""

import re
from functools import lru_cache

VISA_CODE_RE = re.compile(r"(?<![A-Za-z])([A-Ha-h])\s*-\s*(\d{1,2})(?:\s*-\s*(\d{1,2}))?(?!\d)")

# Kiwi part-of-speech tags we keep: nouns, verb/adjective stems, roots,
# foreign words (SL), Chinese characters (SH), numbers (SN).
KEEP_TAGS = ("NNG", "NNP", "NNB", "NR", "VV", "VA", "XR", "SL", "SH", "SN")


@lru_cache(maxsize=1)
def _kiwi():
    from kiwipiepy import Kiwi
    return Kiwi()


def extract_visa_codes(text: str) -> list[str]:
    codes = []
    for m in VISA_CODE_RE.finditer(text):
        code = f"{m.group(1).upper()}-{m.group(2)}"
        if m.group(3):
            codes.append(code)                       # "E-7" also matches "E-7-1"
            code += f"-{m.group(3)}"
        codes.append(code)
    return codes


def tokenize(text: str) -> list[str]:
    tokens = extract_visa_codes(text)
    cleaned = VISA_CODE_RE.sub(" ", text)
    for tok in _kiwi().tokenize(cleaned):
        if tok.tag.startswith(KEEP_TAGS):
            tokens.append(tok.form.lower())
    return tokens
