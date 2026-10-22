"""Thin wrappers around the OpenAI API (embeddings + chat).

Keeping all API calls in one file means switching providers later
(e.g. Upstage Solar) only touches this module.
"""

from functools import lru_cache

from .config import OPENAI_CHAT_MODEL, OPENAI_EMBED_MODEL


@lru_cache(maxsize=1)
def client():
    from openai import OpenAI
    return OpenAI()  # reads OPENAI_API_KEY from the environment


def embed(texts: list[str]) -> list[list[float]]:
    resp = client().embeddings.create(model=OPENAI_EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def chat(messages: list[dict], temperature: float = 0.0) -> tuple[str, dict]:
    resp = client().chat.completions.create(
        model=OPENAI_CHAT_MODEL, messages=messages, temperature=temperature
    )
    usage = resp.usage.model_dump() if resp.usage else {}
    return resp.choices[0].message.content or "", usage
