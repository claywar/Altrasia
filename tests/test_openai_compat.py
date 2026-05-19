"""OpenAI-compatible URL normalization (host vs …/v1 base URLs)."""

from altrasia.inference.openai_compat import (
    chat_completions_url,
    embeddings_url,
    models_url,
)


def test_urls_with_or_without_v1_suffix() -> None:
    host = "http://192.168.1.237:4000"
    root = "http://192.168.1.237:4000/v1"
    assert chat_completions_url(host) == f"{root}/chat/completions"
    assert chat_completions_url(root) == f"{root}/chat/completions"
    assert embeddings_url(host) == f"{root}/embeddings"
    assert models_url(root) == f"{root}/models"
