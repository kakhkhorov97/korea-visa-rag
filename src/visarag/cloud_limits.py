"""Small shared request ledger in private GCS, using generation-match writes.

One object per UTC day. It stores counts and recent timestamps, never questions,
answers or client addresses. A failed provider request still spends its slot.
This is a request cap, not a currency cap or a general bot-defense service.
"""
import json
import math
import threading
import time
from collections import deque
from contextlib import contextmanager
from urllib.parse import urlsplit

from fastapi import HTTPException
from google.api_core.exceptions import NotFound, PreconditionFailed


class CloudUsageLimits:
    def __init__(self, uri: str, per_minute: int, daily_ai: int, daily_total: int,
                 concurrent: int, client=None):
        if min(per_minute, daily_ai, daily_total, concurrent) < 1:
            raise ValueError('API limits must be positive')
        location = urlsplit(uri)
        prefix = location.path.strip('/')
        if (location.scheme != 'gs' or not location.netloc or location.query or
                location.fragment or not prefix.startswith('usage/') or
                '..' in prefix.split('/')):
            raise ValueError('VISARAG_USAGE_URI must be gs://BUCKET/usage/PREFIX')
        if client is None:
            from google.cloud import storage
            client = storage.Client()
        self.bucket = client.bucket(location.netloc)
        self.prefix = prefix
        self.per_minute, self.daily_ai, self.daily_total = per_minute, daily_ai, daily_total
        self.slots = threading.BoundedSemaphore(concurrent)
        self.lock = threading.Lock()
        self.recent = deque()
        self.exhausted = {}  # Only cache denials, until the next UTC day.

    @staticmethod
    def _unavailable():
        return HTTPException(503, 'The demo usage counter is unavailable. Please try again shortly.',
                             headers={'Retry-After': '10'})

    @staticmethod
    def _daily_error(now, ai):
        return HTTPException(429, 'The demo has reached its daily AI limit. Try source search or return tomorrow.'
                             if ai else 'The demo has reached its daily request limit. Please return tomorrow.',
                             headers={'Retry-After': str(int((int(now // 86400) + 1) * 86400 - now) + 1)})

    def _read(self, blob, day):
        try:
            blob.reload(timeout=3, retry=None)
        except NotFound:
            return {'schema': 1, 'day': day, 'ai': 0, 'total': 0, 'recent': []}, 0
        generation = int(blob.generation)
        if blob.size > 65536:
            raise ValueError('Oversized usage state')
        state = json.loads(blob.download_as_bytes(if_generation_match=generation, timeout=3, retry=None))
        if (state.get('schema') != 1 or state.get('day') != day or
                any(type(state.get(k)) is not int or state[k] < 0 for k in ['ai', 'total']) or
                state['ai'] > state['total'] or not isinstance(state.get('recent'), list) or
                len(state['recent']) > 10000 or any(type(t) not in (int, float) or
                not math.isfinite(t) or t < 0 for t in state['recent'])):
            raise ValueError('Invalid usage state')
        return state, generation

    def _charge(self, paid):
        for _ in range(3):
            now = time.time()
            day = int(now // 86400)
            blob = self.bucket.blob(f'{self.prefix}/{day}.json')
            try:
                state, generation = self._read(blob, day)
                if state['total'] >= self.daily_total or (paid and state['ai'] >= self.daily_ai):
                    ai = state['total'] < self.daily_total
                    with self.lock:
                        self.exhausted['ai' if ai else 'all'] = day
                    raise self._daily_error(now, ai)
                state['recent'] = [t for t in state['recent'] if t > now - 60]
                if len(state['recent']) >= self.per_minute:
                    raise HTTPException(429, 'The demo is receiving too many requests. Please wait one minute.',
                                        headers={'Retry-After': '60'})
                state['recent'].append(now)
                state['total'] += 1
                state['ai'] += int(paid)
                blob.upload_from_string(json.dumps(state, separators=(',', ':')), content_type='application/json',
                                        if_generation_match=generation, timeout=3, retry=None)
                return
            except (PreconditionFailed, NotFound):
                # Another instance won the update, or the day object was created.
                continue
            except HTTPException:
                raise
            except Exception:
                # Never return provider URLs, credentials or arbitrary stored text.
                raise self._unavailable() from None
        raise self._unavailable()

    @contextmanager
    def reserve(self, client: str, paid: bool):
        # Intentionally global. Cloud Run proxy addresses are not visitor identities,
        # and trusting arbitrary forwarded headers would permit quota bypass.
        acquired = False
        if paid:
            acquired = self.slots.acquire(blocking=False)
            if not acquired:
                raise HTTPException(503, 'The assistant is busy. Please try again shortly.',
                                    headers={'Retry-After': '5'})
        try:
            now = time.time()
            with self.lock:
                day = int(now // 86400)
                if self.exhausted.get('all') == day or (paid and self.exhausted.get('ai') == day):
                    raise self._daily_error(now, self.exhausted.get('all') != day)
                while self.recent and self.recent[0] <= now - 60:
                    self.recent.popleft()
                if len(self.recent) >= self.per_minute:
                    raise HTTPException(429, 'The demo is receiving too many requests. Please wait one minute.',
                                        headers={'Retry-After': '60'})
                self.recent.append(now)  # Also bounds repeated failed Storage requests.
            self._charge(paid)
            yield
        finally:
            if acquired:
                self.slots.release()
