from __future__ import annotations

from typing import Any

from altrasia.orchestrator.idle_task_affinity import format_task_hints_for_prompt


def relationship_snippet(memory: Any, speaker_id: str, other_id: str, *, max_chars: int = 400) -> str:
    if not memory:
        return ""
    try:
        rows = memory.store.search_loci(
            "mind", speaker_id, f"relationship:{other_id}", limit=1
        )
        if not rows:
            return ""
        val = (rows[0].get("value") or "").strip()
        return val[:max_chars]
    except Exception:
        return ""


def culture_snippet(memory: Any, scene_id: str, *, max_chars: int = 500) -> str:
    if not memory:
        return ""
    parts: list[str] = []
    for key in ("culture:norms", "culture:recent"):
        try:
            rows = memory.store.search_loci("world", scene_id, key, limit=1)
            if rows:
                parts.append(f"{key}: {(rows[0].get('value') or '')[:max_chars]}")
        except Exception:
            continue
    return "\n".join(parts)[:max_chars]


def _tone_guidance(tone: str, other_name: str, role_label: str | None) -> list[str]:
    tone = (tone or "roleplay").strip().lower()
    if tone == "professional":
        role_line = (
            f"Your role in this world: {role_label}."
            if role_label
            else "Ground this exchange in your professional role and existing facts."
        )
        return [
            role_line,
            "This is ambient workplace color—not main plot. Favor realistic small talk, "
            "curiosity, and role-appropriate learning over invented drama.",
            "Before asserting a workplace fact (project status, policy, client, deadline), "
            "use memory_search on your mind pool or diary_search for what you already witnessed.",
            "Do not fabricate confidential details, client names, or dates; ask a question "
            "or share a grounded observation instead.",
            f"Do NOT write dialogue, actions, or lines for {other_name}.",
        ]
    return [
        "This is ambient character color—keep it light and in-voice.",
        "Imagination is fine for tone; avoid contradicting established mind or world facts.",
        f"Do NOT write dialogue, actions, or lines for {other_name}.",
    ]


def banter_system_addendum(
    services: Any,
    *,
    world_id: str,
    scene_id: str,
    speaker_id: str,
    activity: dict[str, Any],
    members: dict[str, dict[str, Any]],
    recent_session_lines: list[str],
    tone: str = "roleplay",
    task_hints: list[dict[str, Any]] | None = None,
    digest_active: bool = False,
) -> str:
    order = activity.get("speakingOrder") or []
    other_id = next((c for c in order if c != speaker_id), None)
    other_name = (
        (members.get(other_id) or {}).get("displayName", "the other person")
        if other_id
        else "your counterpart"
    )
    speaker = members.get(speaker_id) or {}
    role_label = speaker.get("sceneRole") or speaker.get("title")
    lines = [
        "Ambient sidebar banter: the operator has not singled you out.",
        f"You are speaking with {other_name} in a brief private exchange at the scene.",
        "React to what they last said or advance the thread; do not repeat the same beat.",
        "Do not call scene_summon or order group assembly.",
    ]
    lines.extend(_tone_guidance(tone, other_name, role_label))
    rel = relationship_snippet(services.memory, speaker_id, other_id or "")
    if rel:
        lines.append(f"\nYour relationship notes about {other_name}:\n{rel}")
    cult = culture_snippet(services.memory, scene_id)
    if cult:
        lines.append(f"\nShared culture / norms:\n{cult}")
    if recent_session_lines:
        excerpt = "\n".join(f"- {t[:200]}" for t in recent_session_lines[-2:])
        lines.append(f"\nRecent lines in this banter session:\n{excerpt}")
    if digest_active or task_hints:
        lines.append(
            "Before inventing new topics, use diary_search / memory_search on what "
            "the operator and cast recently did. Sidebar chat should help you process "
            "that—not start unrelated drama."
        )
    task_block = format_task_hints_for_prompt(task_hints or [], members)
    if task_block:
        lines.append(f"\n{task_block}")
        if (tone or "roleplay").strip().lower() == "professional":
            lines.append(
                "When tasks are listed above, lean sidebar chat toward coordination, "
                "blockers, and what you already know—use memory_search before new claims."
            )
        else:
            lines.append(
                "When tasks are listed above, you may weave them into banter naturally "
                "without turning this into a formal status meeting."
            )
    return "\n".join(lines)


def floor_focus_addendum(
    hold: dict[str, Any],
    members: dict[str, dict[str, Any]],
    character_id: str,
) -> str:
    claimed = hold.get("claimedBy")
    awaiting = list(hold.get("awaitingAddressees") or [])
    if claimed == character_id:
        return (
            "You claimed the room's attention. Others have paused sidebar banter. "
            "Speak clearly to your point."
        )
    if character_id in awaiting:
        name = (members.get(claimed) or {}).get("displayName", "Someone")
        return (
            f"{name} addressed you directly. Side banter is paused. "
            "Reply to them; do not restart unrelated sidebar chat."
        )
    return (
        "Sidebar banter is paused while the room focuses on a question or address. "
        "Keep your reply brief and on-topic if you speak."
    )
