# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

People asking about Korean visa and residence rules in English or Korean.
Sean also uses this project in his portfolio for recruiters to try.

## Product Purpose

Help visitors find official visa information and read an answer alongside its
source citations. This is a portfolio demonstration, not an immigration authority.

## Positioning

Retrieves selected official Korean statutory passages with BM25 and Chroma
vector search, then uses Gemini to answer from those passages.

## Capabilities and Constraints

- Existing FastAPI backend and plain HTML, CSS and JavaScript frontend.
- English and Korean questions; keyword, meaning and combined retrieval.
- Current public corpus: 39 chunks covering 21 broad visa categories.
- Source links, original passages and general-information notice stay accessible.
- Search-only mode remains available without AI calls.
- Preserve escaping, citation behavior, backend secrets and persistent index.
- Low ongoing cost matters. Do not invent comprehensive coverage or accuracy claims.
- Sean approved the generated modern design and its implementation on the public demo.
- No staging, commits or pushes. Publication needs the user's authorization.

## Brand Commitments

Korea Visa Assistant / 체류자격 도우미. Sean requested a modern design demo
using Impeccable and a generated image. No replacement name or logo was requested.

## Evidence on Hand

Existing interface: web/index.html, web/styles.css and web/app.js.
Actual public screenshot: docs/images/cloud-run-gemini.jpg.
Source provenance: data/public_raw/README.md.
Deployment record: docs/EXPANDED_RELEASE_2026-10-26.md.
This record uses product facts already confirmed in the conversation and code;
the generated concept remains separate from actual browser screenshots.

## Product Principles

- Put the question and supporting sources within easy reach.
- Separate retrieved evidence from generated interpretation.
- State coverage honestly and keep unsupported questions outside the answer.
- Keep the public demo straightforward to try without an account.
