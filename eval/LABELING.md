# Evaluation labels

`questions.jsonl` contains the original 12 questions, labeled against the public
statute corpus fetched on 2026-10-24. Labels follow the source provisions, not the
rankings. `label_note` states the supporting provision and any missing detail.

- Six questions have coverage for their general question.
- Five have partial coverage and remain in retrieval scores. Permission rules do
  not establish D-2/D-4 work eligibility or hours. The D-10 statutory ceiling does
  not establish cumulative job-search extensions. The E-7 category definition
  does not establish occupation-specific qualifications.
- One geography question is out of scope and has no relevant legal chunks.

Several relevant chunks can be complementary. For example, a visa-category row
and the general permission rule both help answer a student-work question. Hit@5
means at least one appeared; it does not prove a complete answer. Recall measures
how many of the labeled chunks appeared. MRR uses the first relevant chunk in
the top 20 candidates. None of these measures legal answer accuracy.

Run the matching public corpus, separately from the local HiKorea index:

```bash
VISARAG_RAW_DIR="$PWD/data/public_raw" VISARAG_DATA_DIR="$PWD/data/public_cache" python scripts/build_index.py
python eval/run_eval.py
```

Without a key, only BM25 is evaluated. `--answers` makes additional paid calls;
its citation rate is not an accuracy score. Read generated answers against the
sources before claiming answer quality. `--corpus local --questions PATH` needs
labels made for that local corpus. Missing chunk IDs cause an error.

To review or expand labels, read every candidate source in full, include all
provisions that materially support the question, and record omissions. Do not
add IDs solely because a retrieval method ranked them. Refresh labels and rerun
scores when a source, extractor, or chunk boundary changes.
