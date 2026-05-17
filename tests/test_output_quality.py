import json
from pathlib import Path

from altrasia.memory.strip_reasoning import strip_from_message_payload


def test_oq3_reasoning_stripped_from_payload() -> None:
    fixture = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "strip-reasoning"
        / "qwen-think-tags.json"
    )
    data = json.loads(fixture.read_text(encoding="utf-8"))
    raw = data["input"]
    out = strip_from_message_payload({"content": raw})
    assert "secret" not in out
    assert "Hello" in out and "world" in out
