from __future__ import annotations


def normalize_openai_base_url(base_url: str) -> str:
    """Accept host:port or …/v1; always return an OpenAI API root ending in /v1."""
    url = base_url.strip().rstrip("/")
    if url.endswith("/v1"):
        return url
    return url + "/v1"


def chat_completions_url(base_url: str) -> str:
    return f"{normalize_openai_base_url(base_url)}/chat/completions"


def embeddings_url(base_url: str) -> str:
    return f"{normalize_openai_base_url(base_url)}/embeddings"


def models_url(base_url: str) -> str:
    return f"{normalize_openai_base_url(base_url)}/models"
