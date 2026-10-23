# Source documents go here

Two ways to add documents:

1. **Laws (automatic):** run `python scripts/fetch_laws.py` after setting `LAW_API_OC` in `.env`.
2. **Guides (manual):** copy text from official pages such as the HiKorea visa guides
   (https://www.hikorea.go.kr) or the Korea Immigration Service manuals, and save each one as a
   `.txt` file with this header:

```
---
title: HiKorea 체류자격별 안내 - 구직(D-10)
source_url: https://www.hikorea.go.kr/...
doc_type: guide
retrieved: 2026-10-22
---
(paste the text here)
```

Use only official government sources, and always fill in `source_url` and `retrieved`:
the assistant cites them in every answer, and visa rules change often.

URL anchors such as `#article-2` are preserved. To add an inline metadata comment,
put whitespace before `#`, as in `doc_type: guide # split by heading`.
