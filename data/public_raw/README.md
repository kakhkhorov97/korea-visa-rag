# Public statute corpus

This directory is the only source-data directory copied into the public Docker
image. It contains 17 selected articles of the Immigration Act and its
Enforcement Decree, plus five selected statutory annex rows. Retrieved 2026-10-24.
Each file records its official URL, retrieval date and extracted-text SHA-256.

Articles were fetched with `python scripts/fetch_public_statutes.py` from the
official public article viewer. No account or LAW_API_OC is needed. Refreshing
sources is a deliberate maintenance step, never a network operation at startup.

The annex excerpts were extracted with Poppler `pdftotext -layout` and checked
against rendered PDF pages. `python scripts/extract_statute_annexes.py` reproduces
the extraction from pinned PDF file IDs. It verifies the source-file hashes
before applying reviewed row boundaries. The D-10 stay-limit excerpt preserves
the complete exception footnote. Table spacing is retained; these are excerpts,
not complete annexes or translations.

This is a small demonstration corpus. It omits administrative guidance,
occupation-specific qualifications, student-work conditions, and cumulative
D-10 extension policies. A source's statutory ceiling must not be treated as a
promise that a particular applicant receives that stay period.

## Reuse basis

The public package contains statutory text, which is listed in Article 7(1) of
the Korean Copyright Act among works not protected by that Act. Source:
https://www.law.go.kr/lsLinkCommonInfo.do?chrClsCd=010202&lsJoLnkSeq=1033063839
This statement applies to the selected statutory text, not to website branding,
guides or other government publications. Attribution and provenance remain in
every source file. The project's MIT license covers its code.

The HiKorea manual, its extracts in `data/raw/`, and its original HWP in
`data/originals/` are excluded from the image. See `data/SOURCES.md` for their
separate reuse restrictions. Excluding a file from Docker does not remove it
from Git history or an existing GitHub repository.
