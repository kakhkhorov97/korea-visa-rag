# 44-chunk beta review, 2026-10-26

`KIWI_LIGHTWEIGHT=true .venv/bin/python eval/run_beta_review.py --answers`
completed 36 synthetic English/Korean questions against 44 selected public
statute chunks. The detailed local report is `eval/results/beta_review.json`
(ignored because it contains complete generated answers and usage details).
The source-based retrieval labels cover 32 questions; 20 were marked covered
and 12 partial. Labels were selected from relevant official chunks before
scoring, not to favor a retrieval method. The original 12-question baseline
remains separately available in `eval/public_expanded_baseline.json`.

| Retrieval, 32 labeled questions | hit@5 | recall@5 | MRR |
|---|---:|---:|---:|
| BM25 | 0.812 | 0.703 | 0.702 |
| Vector | 0.969 | 0.891 | 0.827 |
| Hybrid | 0.969 | 0.891 | 0.935 |

The real AI run returned 29 responses and seven failures. Ten of the 29
responses abstained. One failure was a provider-unavailable response; six were
rejected by evidence checks. Those rejected replies were never displayed as
legal answers. After this run, the code was changed to return the retrieved
original passages with an explicit notice for these failures, and tests verify
that fallback without another provider call. The **36 AI responses have not
been rerun or independently legally reviewed under that change**.

Manual spot checks found the F-3 source row lists D-1, D-2 and D-4 through
E-7, so the generated D-3 exclusion was supported. A separate early test had
misnamed residence (F-2) as residence (F-3); a narrow code/label check was
added before the 36-question run. This check does not verify every translation
or inference. Questions about student work hours, exact supporting documents,
occupation qualifications and individual eligibility remain outside or only
partly inside this small corpus. A retrieval hit and an exact supporting quote
are insufficient to claim legal answer accuracy.

Before describing this beta as reliable legal guidance, have a qualified human
review every generated claim, the original Korean article/annex, all conditions
and exceptions, and the official current version. Keep the app labeled as
general information and direct users to 1345 or HiKorea for decisions.
