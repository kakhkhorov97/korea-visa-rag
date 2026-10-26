"""Paced bilingual beta review; saves failures and leaves legal review unscored.

Run --answers to make real provider calls. Synthetic questions only. Reuses each
question embedding within this run so vector and hybrid do not embed it twice.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import os
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--answers',action='store_true')
    p.add_argument('--interval',type=float,default=6)
    p.add_argument('--output',type=Path,default=ROOT/'eval/results/beta_review.json')
    args=p.parse_args()
    if args.interval<0:p.error('interval must be nonnegative')
    os.environ['VISARAG_RAW_DIR']=str(ROOT/'data/public_raw')
    os.environ['VISARAG_DATA_DIR']=str(ROOT/'data/public_cache')
    from visarag.assistant import VisaAssistant
    from visarag.config import GEMINI_CHAT_MODEL,GEMINI_EMBED_MODEL
    from visarag.errors import ProviderError
    from visarag.metrics import hit_at_k,recall_at_k,reciprocal_rank,summarize
    engine=VisaAssistant()
    if args.answers and not engine.use_llm:p.error('--answers requires Gemini')
    modes=engine.available_modes
    if 'vector' in engine.retrievers:
        vector=engine.retrievers['vector']; original=vector.query_embed_fn; cache={}
        def cached(texts):
            key=tuple(texts)
            if key not in cache:cache[key]=original(texts)
            return cache[key]
        vector.query_embed_fn=cached
    questions=[json.loads(line) for line in (ROOT/'eval/beta_questions.jsonl').read_text().splitlines()]
    unknown={cid for q in questions for cid in q['relevant']}-set(engine.by_id)
    if unknown:raise ValueError(f'Missing source IDs: {unknown}')
    report={'created':datetime.now(timezone.utc).isoformat(),'chunks':len(engine.chunks),
            'chat_model':GEMINI_CHAT_MODEL,'embedding_model':GEMINI_EMBED_MODEL,'rows':[],
            'manual_legal_review':'pending; no accuracy score claimed'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    for q in questions:
        start=time.monotonic(); row={**q,'rankings':{}}
        try:
            for mode in modes:
                row['rankings'][mode]=[cid for cid,_ in engine.retrievers[mode].search(q['question'])]
            if args.answers:
                a=engine.ask(q['question'],mode='hybrid')
                row.update(answer=a.text,cited=a.cited,sources=[s.chunk_id for s in a.sources],
                           evidence=a.evidence,usage=a.usage,latency_s=a.latency_s,
                           refused=not bool(a.sources),manual_review='pending')
        except ProviderError as e:
            row['error']=str(e)
        except Exception as e:
            row['error']=type(e).__name__  # Never copy arbitrary upstream response text.
        report['rows'].append(row)
        report['retrieval']={}
        for mode in modes:
            scored=[]
            for r in report['rows']:
                if r['relevant'] and mode in r['rankings']:
                    ranks=r['rankings'][mode]; rel=set(r['relevant'])
                    scored.append({'hit':hit_at_k(ranks,rel,5),'recall':recall_at_k(ranks,rel,5),
                                   'rr':reciprocal_rank(ranks,rel)})
            if scored:report['retrieval'][mode]=summarize(scored,5)
        report['completed']=len(report['rows'])
        report['errors']=sum('error' in r for r in report['rows'])
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(q['id'], 'error' if 'error' in row else 'checked', flush=True)
        if q!=questions[-1]:time.sleep(max(0,args.interval-(time.monotonic()-start)))
    print(args.output,flush=True)


if __name__=='__main__':main()
