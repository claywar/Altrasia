from altrasia.orchestrator.chat_messages import (
    scene_messages_for_llm,
    thinking_safe_chat_messages,
)


def test_skips_empty_interrupted_and_narrates_cast_lines() -> None:
    rows = [
        {"role": "user", "outputText": "Hello", "streamStatus": "final"},
        {"role": "assistant", "outputText": "", "streamStatus": "interrupted"},
        {"role": "assistant", "outputText": "", "streamStatus": "interrupted"},
        {"role": "user", "outputText": "Again?", "streamStatus": "final"},
        {"role": "assistant", "outputText": "part a", "streamStatus": "final"},
        {"role": "assistant", "outputText": "part b", "streamStatus": "interrupted"},
    ]
    turns = scene_messages_for_llm(rows)
    assert turns == [
        {"role": "user", "content": "Hello"},
        {"role": "user", "content": "Again?"},
        {"role": "user", "content": "[Scene] part a"},
        {"role": "user", "content": "[Scene] part b"},
    ]
    assert all(t["role"] == "user" for t in turns)


def test_thinking_safe_chat_messages_rewrites_assistant_content() -> None:
    messages = [
        {"role": "system", "content": "You are Tom."},
        {"role": "user", "content": "Hello."},
        {"role": "assistant", "content": "Rachel: Hi there."},
    ]
    safe = thinking_safe_chat_messages(messages)
    assert safe[-1] == {"role": "user", "content": "[Scene] Rachel: Hi there."}


def test_thinking_safe_preserves_tool_call_assistant() -> None:
    messages = [
        {"role": "system", "content": "You are Tom."},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "memory_search", "arguments": "{}"}}],
        },
        {"role": "tool", "tool_call_id": "c1", "content": "[]"},
    ]
    safe = thinking_safe_chat_messages(messages)
    assert safe[1]["role"] == "assistant"
    assert safe[1].get("tool_calls")


def test_cast_assistant_becomes_scene_user_context() -> None:
    rows = [
        {"role": "user", "outputText": "Hello everyone.", "streamStatus": "final"},
        {
            "role": "assistant",
            "characterId": "char-rachel-kim",
            "outputText": 'Rachel Kim: "We should align on scope."',
            "streamStatus": "final",
        },
    ]
    turns = scene_messages_for_llm(rows)
    assert turns == [
        {"role": "user", "content": "Hello everyone."},
        {
            "role": "user",
            "content": '[Scene] Rachel Kim: "We should align on scope."',
        },
    ]
