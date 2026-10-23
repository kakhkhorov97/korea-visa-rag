"""Gemini API wrappers for embeddings and cited answers.

All provider calls stay here so the assistant, web app and Telegram bot
can share the same engine without knowing the SDK's request format.
"""

from functools import lru_cache

from google.genai import types

from .config import GEMINI_API_KEY, GEMINI_CHAT_MODEL, GEMINI_EMBED_MODEL


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
        raise ValueError("Gemini did not return one embedding per input text.")
    return [e.values for e in embeddings]


def embed_query(texts: list[str]) -> list[list[float]]:
    """Use Gemini's query task for questions, paired with document embeddings."""
    return embed(texts, task_type="RETRIEVAL_QUERY")


def chat(messages: list[dict], temperature: float = 0.0) -> tuple[str, dict]:
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
        config=types.GenerateContentConfig(system_instruction=system, temperature=temperature),
    )
    if not resp.text:
        raise ValueError("Gemini returned no answer text.")
    usage = resp.usage_metadata
    # Keep the shared Answer/evaluation token keys independent of the SDK.
    return resp.text, {
        "prompt_tokens": (usage.prompt_token_count or 0) if usage else 0,
        "completion_tokens": (usage.candidates_token_count or 0) if usage else 0,
        "total_tokens": (usage.total_token_count or 0) if usage else 0,
    }
