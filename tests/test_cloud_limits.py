"""Shared reservations across fresh instances and conflicting writes, no credentials."""
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from google.api_core.exceptions import NotFound, PreconditionFailed
from visarag.cloud_limits import CloudUsageLimits


class Store:
    def __init__(self):
        self.rows = {}
        self.conflict = False
        self.failure = False
        self.writes = 0

    def bucket(self, name):
        return self

    def blob(self, name):
        store = self
        class Blob:
            def reload(self, **kwargs):
                if store.failure:
                    raise RuntimeError('secret-key-in-upstream-url')
                if name not in store.rows:
                    raise NotFound('missing')
                self.generation, data = store.rows[name]
                self.size = len(data)

            def download_as_bytes(self, if_generation_match, **kwargs):
                version, data = store.rows[name]
                if version != if_generation_match:
                    raise PreconditionFailed('read race')
                return data

            def upload_from_string(self, data, if_generation_match, **kwargs):
                version = store.rows.get(name, (0, b''))[0]
                if store.conflict:
                    store.conflict = False
                    competing = json.loads(data)
                    store.rows[name] = (version + 1, json.dumps(competing).encode())
                    raise PreconditionFailed('another instance reserved first')
                if version != if_generation_match:
                    raise PreconditionFailed('write race')
                store.rows[name] = (version + 1, data.encode())
                store.writes += 1
        return Blob()


def limiter(store, minute=20, ai=2, total=10):
    return CloudUsageLimits('gs://private/usage/beta', minute, ai, total, 1, client=store)


def test_shared_daily_cap_survives_new_instances_and_provider_failure():
    store = Store()
    with pytest.raises(RuntimeError):
        with limiter(store).reserve('proxy', True):
            raise RuntimeError('provider failed')
    with limiter(store).reserve('different-proxy', True):
        pass
    with pytest.raises(HTTPException) as error:
        with limiter(store).reserve('new-instance', True):
            pytest.fail('Must reject before AI')
    assert error.value.status_code == 429
    with limiter(store).reserve('proxy', False):
        pass  # Free keyword search remains available after the AI cap.


def test_concurrent_creation_conflict_does_not_lose_reservation():
    store = Store(); store.conflict = True
    with limiter(store, ai=1).reserve('proxy', False):
        pass
    state = json.loads(next(iter(store.rows.values()))[1])
    assert state['total'] == 2 and state['ai'] == 0


def test_global_minute_and_total_caps_apply_across_clients_and_instances():
    store = Store()
    with limiter(store, minute=1).reserve('alice', False):
        pass
    with pytest.raises(HTTPException) as error:
        with limiter(store, minute=1).reserve('bob', False):
            pass
    assert error.value.status_code == 429
    with pytest.raises(HTTPException):
        with limiter(store, total=1).reserve('charlie', False):
            pass


def test_failed_storage_is_safe_and_releases_concurrency_slot():
    store = Store(); store.failure = True
    limits = limiter(store)
    with pytest.raises(HTTPException) as error:
        with limits.reserve('ignored', True):
            pytest.fail('Unavailable counter must not allow AI')
    assert error.value.status_code == 503 and 'secret' not in str(error.value.detail)
    store.failure = False
    with limits.reserve('ignored', True):
        pass


def test_day_rollover_gets_a_new_ledger(monkeypatch):
    store = Store(); now = [1_000_000.0]
    monkeypatch.setattr('visarag.cloud_limits.time.time', lambda: now[0])
    limits = limiter(store, ai=1)
    with limits.reserve('ignored', True):
        pass
    with pytest.raises(HTTPException):
        with limits.reserve('ignored', True):
            pass
    now[0] += 86400
    with limits.reserve('ignored', True):
        pass
    assert len(store.rows) == 2


def test_corrupt_counter_never_resets_to_zero():
    store = Store()
    with limiter(store).reserve('ignored', True):
        pass
    key = next(iter(store.rows)); store.rows[key] = (2, b'{"ai": 0}')
    with pytest.raises(HTTPException) as error:
        with limiter(store).reserve('ignored', True):
            pass
    assert error.value.status_code == 503
    assert store.writes == 1


@pytest.mark.parametrize('uri', ['gs://bucket/releases/snapshot', 'https://bucket/usage/beta', 'gs://bucket/usage/../x'])
def test_usage_writer_cannot_target_document_or_snapshot_prefix(uri):
    with pytest.raises(ValueError):
        CloudUsageLimits(uri, 20, 100, 500, 1, client=Store())
