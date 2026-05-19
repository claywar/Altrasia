from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from altrasia.orchestrator.conversation_resolution import is_scene_conversation_unresolved
from altrasia.orchestrator.single_speaker import operator_trigger_text, trigger_invites_ensemble

log = logging.getLogger(__name__)

ISO = lambda: datetime.now(timezone.utc).isoformat()

ENSEMBLE_KIND = "ensemble_discussion"
_JUDGE_MARKER = "discussion sufficiency judge"


def _parse_activity(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def get_ensemble_discussion(scene: dict[str, Any] | None) -> dict[str, Any] | None:
    if not scene:
        return None
    data = _parse_activity(scene.get("activityJson"))
    if not data or data.get("kind") != ENSEMBLE_KIND:
        return None
    return data


def ensure_ensemble_discussion(
    store: Any,
    scene_id: str,
    *,
    operator_message_id: str | None = None,
) -> dict[str, Any]:
    scene = store.get_scene(scene_id)
    if not scene:
        raise ValueError("scene not found")
    existing = get_ensemble_discussion(scene)
    if existing:
        return existing
    activity = {
        "kind": ENSEMBLE_KIND,
        "operatorMessageId": operator_message_id,
        "signals": [],
        "orchestratorJudgement": None,
        "startedAt": ISO(),
    }
    store.update_scene(scene_id, activityJson=json.dumps(activity), updatedAt=ISO())
    return activity


def clear_ensemble_discussion(store: Any, scene_id: str) -> None:
    scene = store.get_scene(scene_id)
    if not scene:
        return
    data = _parse_activity(scene.get("activityJson"))
    if data and data.get("kind") == ENSEMBLE_KIND:
        store.update_scene(scene_id, activityJson=None, updatedAt=ISO())


def record_character_signal(
    store: Any,
    scene_id: str,
    character_id: str,
    *,
    sufficient: bool,
    gaps: list[str] | None = None,
    note: str = "",
    message_id: str | None = None,
) -> dict[str, Any]:
    scene = store.get_scene(scene_id)
    if not scene:
        raise ValueError("scene not found")
    activity = get_ensemble_discussion(scene) or ensure_ensemble_discussion(store, scene_id)
    cleaned_gaps = [g.strip() for g in (gaps or []) if g and str(g).strip()]
    signal = {
        "characterId": character_id,
        "sufficient": bool(sufficient),
        "gaps": cleaned_gaps,
        "note": (note or "").strip()[:500],
        "messageId": message_id,
        "at": ISO(),
    }
    signals: list[dict[str, Any]] = list(activity.get("signals") or [])
    signals = [s for s in signals if s.get("characterId") != character_id]
    signals.append(signal)
    activity["signals"] = signals[-24:]
    store.update_scene(scene_id, activityJson=json.dumps(activity), updatedAt=ISO())
    return signal


def apply_tool_log_signals(
    store: Any,
    scene_id: str,
    character_id: str,
    tool_log: list[dict[str, Any]],
    *,
    message_id: str | None = None,
) -> int:
    """Persist discussion_signal tool calls from a generation into scene state."""
    count = 0
    for entry in tool_log:
        if entry.get("name") != "discussion_signal":
            continue
        args = entry.get("arguments") or {}
        record_character_signal(
            store,
            scene_id,
            character_id,
            sufficient=bool(args.get("sufficient")),
            gaps=args.get("gaps") if isinstance(args.get("gaps"), list) else [],
            note=str(args.get("note") or ""),
            message_id=message_id,
        )
        count += 1
    return count


def _character_influence_summary(signals: list[dict[str, Any]]) -> str:
    if not signals:
        return "No cast members filed discussion_signal."
    lines: list[str] = []
    for s in signals[-12:]:
        cid = s.get("characterId", "?")
        if s.get("sufficient"):
            lines.append(f"- {cid}: considers discussion sufficient")
        else:
            gaps = s.get("gaps") or []
            gap_txt = "; ".join(gaps[:4]) if gaps else (s.get("note") or "more needed")
            lines.append(f"- {cid}: not sufficient — {gap_txt}")
    return "\n".join(lines)


def _transcript_excerpt(store: Any, world_id: str, scene_id: str, limit: int = 16) -> str:
    rows = store.list_messages(world_id, scene_id=scene_id)[-limit:]
    lines: list[str] = []
    members = {m["characterId"]: m for m in store.list_world_characters(world_id)}
    for m in rows:
        text = (m.get("outputText") or "").strip()
        if not text:
            continue
        if m.get("role") == "assistant" and m.get("characterId"):
            name = (members.get(m["characterId"]) or {}).get("displayName") or m["characterId"]
            lines.append(f"{name}: {text[:600]}")
        elif m.get("role") != "assistant":
            lines.append(f"Operator: {text[:600]}")
    return "\n".join(lines)


def _parse_judgement_json(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    return None


async def run_orchestrator_judgement(
    svc: Any,
    *,
    world_id: str,
    scene_id: str,
    operator_prompt: str,
    character_signals: list[dict[str, Any]],
    transcript: str,
    deliverables_note: str = "",
) -> dict[str, Any]:
    """LLM pass: is the group discussion informationally sufficient?"""
    system = (
        f"You are a {_JUDGE_MARKER} for a multi-character workplace scene.\n"
        "Given the operator request, cast discussion signals, and transcript excerpt, "
        "decide if enough has been surfaced for the operator to act — not whether "
        "everyone agrees, but whether major gaps are still unaddressed.\n"
        "Discussion sufficiency is separate from post-discussion deliverables "
        "(e.g. a named report still owed to the operator).\n"
        "Respond with ONLY JSON:\n"
        '{"sufficient": true|false, "reason": "...", "outstandingGaps": ["..."], '
        '"deliverablesOutstanding": ["..."], "influencedByCharacters": true|false}'
    )
    deliverables_block = deliverables_note or "No post-discussion deliverables pending."
    user = (
        f"## Operator request\n{operator_prompt[:1200]}\n\n"
        f"## Post-discussion deliverables (informational)\n{deliverables_block}\n\n"
        f"## Cast discussion_signal filings\n{_character_influence_summary(character_signals)}\n\n"
        f"## Transcript (recent)\n{transcript[:8000]}"
    )
    from altrasia.world_config import get_world_config

    timeout = float(get_world_config(svc.store, world_id).get("inferenceTimeoutSeconds", 180))
    resp = await svc.llm.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        None,
        timeout=timeout,
    )
    raw = (resp.get("choices") or [{}])[0].get("message", {}).get("content", "")
    parsed = _parse_judgement_json(str(raw))
    if not parsed:
        return {
            "sufficient": False,
            "reason": "judgement_parse_failed",
            "outstandingGaps": [],
            "influencedByCharacters": bool(character_signals),
            "at": ISO(),
        }
    return {
        "sufficient": bool(parsed.get("sufficient")),
        "reason": str(parsed.get("reason") or "")[:500],
        "outstandingGaps": [
            str(g)[:200] for g in (parsed.get("outstandingGaps") or [])[:8]
        ],
        "deliverablesOutstanding": [
            str(g)[:200] for g in (parsed.get("deliverablesOutstanding") or [])[:8]
        ],
        "influencedByCharacters": bool(parsed.get("influencedByCharacters", character_signals)),
        "at": ISO(),
    }


def _signals_force_continue(signals: list[dict[str, Any]]) -> tuple[bool, str]:
    if not signals:
        return False, "no_character_signals"
    recent = signals[-12:]
    if any(not s.get("sufficient") for s in recent):
        gaps = []
        for s in recent:
            if not s.get("sufficient"):
                gaps.extend(s.get("gaps") or [])
        return True, "character_reported_gaps"
    if len(recent) >= 2 and all(s.get("sufficient") for s in recent):
        return False, "characters_report_sufficient"
    return False, "signals_inconclusive"


async def assess_discussion_continuation(
    svc: Any,
    *,
    world_id: str,
    scene_id: str,
    cfg: dict[str, Any],
    current_depth: int,
) -> tuple[bool, str, dict[str, Any]]:
    """
    Whether the ensemble chain should continue past the soft depth limit.

    Returns (unresolved, reason, detail dict for events/UI).
    """
    detail: dict[str, Any] = {"depth": current_depth}
    if not cfg.get("continueUntilResolved", True):
        unresolved, reason = is_scene_conversation_unresolved(svc.store, world_id, scene_id)
        detail["mode"] = "heuristic_only"
        detail["unresolved"] = unresolved
        detail["reason"] = reason
        return unresolved, reason, detail

    scene = svc.store.get_scene(scene_id)
    rows = svc.store.list_messages(world_id, scene_id=scene_id)
    op_line = operator_trigger_text(rows)
    invited = trigger_invites_ensemble(op_line)
    ensemble = get_ensemble_discussion(scene)
    signals: list[dict[str, Any]] = list((ensemble or {}).get("signals") or [])
    detail["characterSignals"] = len(signals)

    heuristic_unresolved, heuristic_reason = is_scene_conversation_unresolved(
        svc.store, world_id, scene_id
    )
    detail["heuristic"] = {"unresolved": heuristic_unresolved, "reason": heuristic_reason}

    if not invited and not ensemble:
        detail["mode"] = "heuristic"
        return heuristic_unresolved, heuristic_reason, detail

    force_continue, signal_reason = _signals_force_continue(signals)
    if force_continue:
        detail["mode"] = "character_signals"
        detail["unresolved"] = True
        detail["reason"] = signal_reason
        return True, signal_reason, detail

    base = int(cfg.get("maxContinueDepth", 2))
    run_llm = bool(cfg.get("conversationJudgementEnabled", True))
    at_soft_cap = current_depth + 1 > base
    long_thread = len(
        [
            m
            for m in rows
            if m.get("role") == "assistant"
            and m.get("characterId")
            and (m.get("streamStatus") or "final") == "final"
        ]
    ) >= max(base, 6)

    from altrasia.orchestrator.discussion_deliverables import deliverables_summary_for_judge

    deliverables_note = deliverables_summary_for_judge(ensemble)

    if run_llm and (at_soft_cap or long_thread or signals):
        try:
            judgement = await run_orchestrator_judgement(
                svc,
                world_id=world_id,
                scene_id=scene_id,
                operator_prompt=op_line,
                character_signals=signals,
                transcript=_transcript_excerpt(svc.store, world_id, scene_id),
                deliverables_note=deliverables_note,
            )
            if ensemble is not None:
                activity = dict(ensemble)
                activity["orchestratorJudgement"] = judgement
                svc.store.update_scene(
                    scene_id, activityJson=json.dumps(activity), updatedAt=ISO()
                )
            detail["mode"] = "orchestrator_judgement"
            detail["judgement"] = judgement
            unresolved = not judgement.get("sufficient")
            reason = str(judgement.get("reason") or "orchestrator_judgement")
            detail["unresolved"] = unresolved
            detail["reason"] = reason
            if signals and judgement.get("influencedByCharacters"):
                detail["characterInfluence"] = _character_influence_summary(signals)
            return unresolved, reason, detail
        except Exception as exc:
            log.warning("discussion judgement failed: %s", exc)
            detail["judgementError"] = str(exc)[:200]

    if signals and all(s.get("sufficient") for s in signals[-6:]):
        detail["mode"] = "character_signals"
        return False, "characters_report_sufficient", detail

    detail["mode"] = "heuristic_fallback"
    detail["unresolved"] = heuristic_unresolved
    detail["reason"] = heuristic_reason
    return heuristic_unresolved, heuristic_reason, detail
