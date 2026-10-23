# Source provenance

The starter corpus contains extracts from the Ministry of Justice / Korea Immigration
Service's HiKorea residence manual. No law Open API registration is needed to index
these local files.

- Official notice: [체류자격별 통합 안내 매뉴얼(최신)](https://www.hikorea.go.kr/board/BoardNtcDetailR.pt?BBS_SEQ=1&BBS_GB_CD=BS10&NTCCTT_SEQ=1062&page=1)
- Downloaded attachment: `261019 체류민원 자격별 안내 매뉴얼.hwp`
- Attachment identifier on retrieval: `APND_SEQ=520`, notice `1062`
- Manual version date: October 19, 2026
- Retrieval date: October 23, 2026
- Original HWP SHA-256: `7effc9d03389e87dc3613db6da873a5d3807ddf4f506df2960f2b017fefabc07`
- Local original: `data/originals/hikorea_residence_manual_20261019.hwp`, ignored by Git

## Included sections

| File | Manual section |
|---|---|
| `raw/hikorea_d2.txt` | 유학(D-2), ending before 기술연수(D-3) |
| `raw/hikorea_d4.txt` | 일반연수(D-4), ending before 취재(D-5) |
| `raw/hikorea_d10.txt` | 구직(D-10), ending before 교수(E-1) |
| `raw/hikorea_e7.txt` | 특정활동(E-7), ending before 계절근로(E-8) |

The files contain Korean source text, not AI summaries or translations. The HWP was
read with pyhwp 0.1b15. A record-level extraction retained paragraph text and table
cells, including table captions. Outer layout tables were flattened into paragraphs;
inner tables were represented as pipe-separated rows with `<br>` for line breaks.
Short cells merged vertically were repeated across their rows to retain row labels.
Each paragraph in the four original sections was checked against the converted text
after whitespace normalization. All 5,266 source paragraphs were retained. This checks
text coverage; it does not establish the correctness of every table interpretation.
Tables with complex merged cells should be checked against the original manual when
answering questions about their thresholds or conditions.

For a fresh manual, download the residence attachment from the official notice,
replace the extracts only after checking paragraph and table coverage, and update the
version, retrieval date and file hash. The notice can change to a newer attachment.

## Source license

The official notice identifies the manual as **KOGL Type 4: attribution,
noncommercial use, no derivatives**. The guide extracts retain Ministry of Justice /
HiKorea attribution. These government documents are not covered by this repository's
MIT software license. The official manual and its stated reuse conditions remain the
reference for the source material.

The manual says updates can lag behind policy changes. The retrieval date records
when this copy was collected; it is not a guarantee that the copy remains current.

## Public deployment corpus

Sean selected statute text for the public demo on 2026-10-24. The container uses
only `data/public_raw/`. The HiKorea extracts and original manual stay outside the
image. Source selection, extraction checks, limitations, and the statutory reuse
basis are recorded in [public_raw/README.md](public_raw/README.md). Container
exclusion does not change any files already tracked or published through Git.
