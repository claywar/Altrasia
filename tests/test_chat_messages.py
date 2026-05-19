from altrasia.orchestrator.chat_messages import scene_messages_for_llm


def test_skips_empty_interrupted_and_merges_trailing_assistant() -> None:
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
        {"role": "assistant", "content": "part a\n\npart b"},
    ]
