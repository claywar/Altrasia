from altrasia.perception.scope import PERSONA_ID, can_perceive


def test_whisper_hidden_from_non_participants() -> None:
    msg = {
        "role": "assistant",
        "characterId": "char-alice",
        "metaJson": '{"communication":{"scope":"whisper","participants":["char-bob"]}}',
    }
    assert can_perceive(viewer_id=PERSONA_ID, message=msg, present=["__persona__", "char-alice"])
    assert not can_perceive(viewer_id="char-carol", message=msg, present=["char-carol"])


def test_persona_always_sees_own_lines() -> None:
    msg = {
        "role": "user",
        "metaJson": '{"communication":{"scope":"whisper","participants":["char-bob"]}}',
    }
    assert can_perceive(viewer_id=PERSONA_ID, message=msg, present=[PERSONA_ID])
