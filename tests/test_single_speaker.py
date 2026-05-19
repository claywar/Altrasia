from altrasia.orchestrator.single_speaker import (
    enforce_single_speaker_output,
    operator_trigger_text,
    single_speaker_system_addendum,
    trigger_invites_ensemble,
)


def test_trigger_invites_ensemble() -> None:
    assert trigger_invites_ensemble("Discuss amongst yourselves how PM works.")
    assert not trigger_invites_ensemble("What is the capital of France?")


def test_operator_trigger_text_from_history() -> None:
    rows = [
        {"role": "user", "outputText": "Hello everyone.", "streamStatus": "final"},
        {
            "role": "assistant",
            "characterId": "char-liam-park",
            "outputText": "Hi.",
            "streamStatus": "final",
        },
    ]
    assert operator_trigger_text(rows) == "Hello everyone."


def test_enforce_keeps_only_named_speaker_block() -> None:
    raw = (
        "**Liam Park:** I see program management as the nervous system.\n\n"
        "**Nina Patel:** I agree—it is connective tissue.\n\n"
        "**Chris Doyle:** I focus on risk."
    )
    out = enforce_single_speaker_output(
        raw,
        "Liam Park",
        ["Nina Patel", "Chris Doyle"],
    )
    assert "Nina Patel" not in out
    assert "Chris Doyle" not in out
    assert "nervous system" in out


def test_single_speaker_addendum_mentions_others() -> None:
    text = single_speaker_system_addendum(
        "Liam Park",
        other_names=["Nina Patel", "Chris Doyle"],
        ensemble_invited=True,
    )
    assert "ONLY Liam Park" in text
    assert "Nina Patel" in text
    assert "separate messages" in text.lower()
    assert "group discussion" in text.lower()
