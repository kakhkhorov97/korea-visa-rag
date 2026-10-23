"""API request reservations stored in SQLite, shared across threads and restarts.

One database/volume per deployment. This is an application request cap, not a
currency budget. Provider-side billing limits are still needed for a paid demo.
"""
import hashlib
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from threading import BoundedSemaphore

from fastapi import HTTPException


class UsageLimits:
    def __init__(self, path: Path, per_minute: int, daily_ai: int, concurrent: int):
        if min(per_minute, daily_ai, concurrent) < 1:
            raise ValueError('API limits must be positive')
        self.path = path
        self.per_minute, self.daily_ai = per_minute, daily_ai
        self.slots = BoundedSemaphore(concurrent)
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS requests (client TEXT, at REAL)')
            db.execute('CREATE INDEX IF NOT EXISTS requests_at ON requests(at)')
            db.execute('CREATE TABLE IF NOT EXISTS daily (day INTEGER PRIMARY KEY, count INTEGER)')

    def connect(self):
        return sqlite3.connect(self.path, timeout=10, isolation_level=None)

    @contextmanager
    def reserve(self, client: str, paid: bool):
        acquired = False
        if paid:
            acquired = self.slots.acquire(blocking=False)
            if not acquired:
                raise HTTPException(503, 'The assistant is busy. Please try again shortly.',
                                    headers={'Retry-After': '5'})
        try:
            now = time.time()
            day = int(now // 86400)
            # Hash IP addresses; never trust an arbitrary forwarded-IP header.
            client_hash = hashlib.sha256(client.encode()).hexdigest()
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                try:
                    db.execute('DELETE FROM requests WHERE at <= ?', (now - 60,))
                    used = db.execute('SELECT count(*) FROM requests WHERE client = ?', (client_hash,)).fetchone()[0]
                    if used >= self.per_minute:
                        raise HTTPException(429, 'Too many requests. Please wait one minute.',
                                            headers={'Retry-After': '60'})
                    if paid:
                        db.execute('DELETE FROM daily WHERE day < ?', (day,))
                        db.execute('INSERT OR IGNORE INTO daily VALUES (?, 0)', (day,))
                        used_ai = db.execute('SELECT count FROM daily WHERE day = ?', (day,)).fetchone()[0]
                        if used_ai >= self.daily_ai:
                            raise HTTPException(429, 'The demo has reached its daily AI limit. Try again tomorrow.',
                                                headers={'Retry-After': str(int((day + 1) * 86400 - now) + 1)})
                        db.execute('UPDATE daily SET count = count + 1 WHERE day = ?', (day,))
                    db.execute('INSERT INTO requests VALUES (?, ?)', (client_hash, now))
                    db.execute('COMMIT')
                except Exception:
                    db.execute('ROLLBACK')
                    raise
            # Failed provider calls also consume the reservation, to limit retry storms.
            yield
        finally:
            if acquired:
                self.slots.release()
