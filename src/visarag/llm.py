"""Gemini API wrappers for embeddings and cited answers.

All provider calls stay here so the assistant, web app and Telegram bot
can share the same engine without knowing the SDK's request format.
"""

from functools import lru_cache, wraps

import httpx
from google.genai import errors

from .errors import ProviderError

from google.genai import types

from .config import GEMINI_API_KEY, GEMINI_CHAT_MODEL, GEMINI_EMBED_MODEL


def provider_call(fn):
    """Never expose upstream error text, request URLs or credentials to callers."""
    @wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except errors.APIError as exc:
            if exc.code == 429:
                raise ProviderError("Gemini's request limit was reached. Please try again later.", 429) from exc
            raise ProviderError("The AI service is unavailable. Please try again later.") from exc
        except httpx.TimeoutException as exc:
            raise ProviderError("The AI service timed out. Please try again.", 504) from exc
        except httpx.TransportError as exc:
            raise ProviderError("The AI service could not be reached. Please try again later.") from exc
    return wrapped


@lru_cache(maxsize=1)
def client():
    from google import genai

    if not GEMINI_API_KEY:
        raise ValueError("Set GEMINI_API_KEY in .env to use Gemini.")
    return genai.Client(
        api_key=GEMINI_API_KEY, vertexai=False,
        # A stalled provider request must not leave a web or Telegram reply waiting forever.
        http_options=types.HttpOptions(
            timeout=60_000, retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


@provider_call
def embed(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Return one vector per text using the text-only gemini-embedding-001 model."""
    if not texts:
        return []
    resp = client().models.embed_content(
        model=GEMINI_EMBED_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(task_type=task_type),
    )
    embeddings = resp.embeddings or []
    if len(embeddings) != len(texts) or any(not e.values for e in embeddings):
        raise ProviderError("Gemini did not return one embedding per input text. Please try again.")
    return [e.values for e in embeddings]


def embed_query(texts: list[str]) -> list[list[float]]:
    """Use Gemini's query task for questions, paired with document embeddings."""
    return embed(texts, task_type="RETRIEVAL_QUERY")


@provider_call
def chat(messages: list[dict], temperature: float = 0.0, *, response_schema: dict | None = None) -> tuple[str, dict]:
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    contents = [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part.from_text(text=m["content"])],
        )
        for m in messages if m["role"] != "system"
    ]
    resp = client().models.generate_content(
        model=GEMINI_CHAT_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system, temperature=temperature, max_output_tokens=1536,
            response_mime_type='application/json' if response_schema else None,
            response_json_schema=response_schema,
        ),
    )
    if not resp.text:
        raise ProviderError("Gemini returned no answer text. Please try again.")
    usage = resp.usage_metadata
    # Keep the shared Answer/evaluation token keys independent of the SDK.
    return resp.text, {
        "prompt_tokens": (usage.prompt_token_count or 0) if usage else 0,
        "completion_tokens": (usage.candidates_token_count or 0) if usage else 0,
        "total_tokens": (usage.total_token_count or 0) if usage else 0,
    }
