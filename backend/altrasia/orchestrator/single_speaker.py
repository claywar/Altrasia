from __future__ import annotations

import re

_ENSEMBLE_CUES = re.compile(
    r"\b(discuss among|discuss amongst|each of you|everyone|all of you|"
    r"round.?table|go around|hear from (each|everyone)|your perspectives)\b",
    re.I,
)

_SPEAKER_LABEL = re.compile(r"(?:^|\n)\*{0,2}([^*\n:]+?)\*{0,2}\s*:", re.MULTILINE)


def trigger_invites_ensemble(trigger_text: str) -> bool:
    return bool(_ENSEMBLE_CUES.search(trigger_text or ""))


def single_speaker_system_addendum(
    display_name: str,
    *,
    other_names: list[str],
    ensemble_invited: bool = False,
    directed_addressee_name: str | None = None,
    directed_witness: bool = False,
    directed_co_addressees: list[str] | None = None,
) -> str:
    others = [n for n in other_names if n and n.strip() and n.strip() != display_name]
    lines = [
        f"You are ONLY {display_name}. Deliver one in-character public reply as yourself.",
        "Do NOT write dialogue, quotes, summaries, or labeled lines for anyone else in the room.",
    ]
    if others:
        preview = ", ".join(others[:6])
        if len(others) > 6:
            preview += ", …"
        lines.append(f"Other present cast ({preview}) will speak in their own separate messages.")
    if directed_co_addressees:
        names = ", ".join(directed_co_addressees[:6])
        lines.append(
            f"The operator asked you and {names} individually; answer only for yourself. "
            "Do not describe other people's roles, jobs, or biographical facts—they will "
            "speak for themselves in their own messages."
        )
    elif directed_witness and directed_addressee_name:
        lines.append(
            f"The operator asked {directed_addressee_name} directly; only speak if you have "
            "essential information they cannot provide."
        )
    if ensemble_invited:
        lines.append(
            "The operator invited a group discussion: give only your perspective now; "
            "do not script the full conversation."
        )
    return "\n".join(lines)


def operator_trigger_text(rows: list[dict]) -> str:
    """Most recent persona/operator line in scene history."""
    for m in reversed(rows):
        if m.get("role") == "assistant":
            continue
        text = (m.get("outputText") or "").strip()
        if text:
            return text
    return ""


def enforce_single_speaker_output(
    text: str,
    speaker_name: str,
    other_names: list[str] | None = None,
) -> str:
    """If the model attributed lines to multiple cast members, keep only this speaker's block."""
    if not (text or "").strip() or not (speaker_name or "").strip():
        return text
    speaker = speaker_name.strip()
    others = {
        n.strip().lower()
        for n in (other_names or [])
        if n and n.strip() and n.strip().lower() != speaker.lower()
    }
    matches = list(_SPEAKER_LABEL.finditer(text))
    if len(matches) < 2:
        return text

    segments: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        name = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        segments.append((name, text[start:end].strip()))

    labeled_others = {
        name.lower()
        for name, _ in segments
        if name.lower() != speaker.lower() and name.lower() in others
    }
    if not labeled_others:
        return text

    for name, body in segments:
        if name.lower() == speaker.lower():
            prefix = f"{speaker}: "
            if body.lower().startswith(speaker.lower()):
                return body
            return f"{prefix}{body}" if body else text
    first = segments[0]
    if first[0].lower() == speaker.lower():
        return text[: matches[1].start()].strip() if len(matches) > 1 else text
    return text
