from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass
from typing import Any

from altrasia.orchestrator.idle_social_state import (
    dyad_key,
    get_variety_ledger,
    relationship_tension_score,
    seconds_since_dyad_banter,
)
from altrasia.orchestrator.idle_task_affinity import (
    collect_active_tasks_by_character,
    dyad_task_affinity_score,
    task_hints_for_characters,
)
from altrasia.world_config import get_idle_social_config

_TIE_EPSILON = 0.02
_MIN_SCORE = 0.05


@dataclass
class DyadScore:
    a: str
    b: str
    total: float
    factors: dict[str, float]


@dataclass
class DyadPick:
    speaking_order: list[str]
    session_id: str
    rationale: dict[str, Any]


def _participation_weight(cfg: dict[str, Any], character_id: str) -> float:
    weights = cfg.get("idleParticipationWeights") or cfg.get("idleRoundRobinWeights") or {}
    if not isinstance(weights, dict):
        return 1.0
    w = weights.get(character_id)
    if w is None:
        return 1.0
    try:
        return max(0.1, float(w))
    except (TypeError, ValueError):
        return 1.0


def _char_weight(
    ch: dict[str, Any], cfg: dict[str, Any], character_id: str
) -> float:
    sw = float(ch.get("speechWeight", 0.5))
    return sw * _participation_weight(cfg, character_id)


def _recency_factor(seconds_ago: float | None, half_life: float) -> float:
    if seconds_ago is None:
        return 1.0
    if half_life <= 0:
        return 1.0
    return math.exp(-seconds_ago / half_life)


def _weighted_lottery(scores: list[DyadScore], top_k: int) -> DyadScore:
    ordered = sorted(scores, key=lambda s: s.total, reverse=True)
    top = ordered[: max(1, top_k)]
    max_s = top[0].total
    pool = [s for s in top if max_s - s.total <= _TIE_EPSILON] or top
    weights = [max(_MIN_SCORE, s.total) for s in pool]
    return random.choices(pool, weights=weights, k=1)[0]


def score_idle_dyads(
    services: Any,
    *,
    world_id: str,
    scene: dict[str, Any],
    cast: list[str],
) -> list[DyadScore]:
    cfg = get_idle_social_config(services.store, world_id)
    half_life = float(cfg.get("idleSocialRecencyHalfLifeSeconds", 300))
    jitter_scale = float(cfg.get("idleSocialJitter", 0.15))
    ledger = get_variety_ledger(scene)
    chars = {c["characterId"]: c for c in services.store.list_world_characters(world_id)}
    memory = getattr(services, "memory", None)
    task_enabled = cfg.get("idleSocialTaskAffinityEnabled", True)
    tasks_by_char = (
        collect_active_tasks_by_character(
            services, world_id=world_id, scene_id=scene["sceneId"]
        )
        if task_enabled
        else {}
    )
    task_weight = float(cfg.get("idleSocialTaskAffinityWeight", 0.22))

    last_social: dict[str, float] = {}
    for m in reversed(services.store.list_messages(world_id, scene_id=scene["sceneId"])):
        try:
            import json

            meta = json.loads(m.get("metaJson") or "{}")
            orch = meta.get("orchestration") or {}
            if not orch.get("socialIdle"):
                continue
            cid = m.get("characterId")
            if cid and cid not in last_social:
                from datetime import datetime, timezone

                created = m.get("createdAt")
                if created:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    last_social[cid] = (
                        datetime.now(timezone.utc) - dt
                    ).total_seconds()
        except Exception:
            continue
        if len(last_social) >= len(cast):
            break

    scores: list[DyadScore] = []
    ordered_cast = sorted(cast)
    for i, a in enumerate(ordered_cast):
        for b in ordered_cast[i + 1 :]:
            ca = chars.get(a, {})
            cb = chars.get(b, {})
            factors: dict[str, float] = {}
            factors["pairAppetite"] = _char_weight(ca, cfg, a) + _char_weight(cb, cfg, b)
            tension = (
                relationship_tension_score(memory, a, b)
                + relationship_tension_score(memory, b, a)
            ) / 2.0
            factors["relationshipTension"] = tension
            sec = seconds_since_dyad_banter(ledger, a, b)
            factors["recencyDecay"] = _recency_factor(sec, half_life)
            starve_a = 1.25 if a not in last_social else 0.85
            starve_b = 1.25 if b not in last_social else 0.85
            factors["starvation"] = (starve_a + starve_b) / 2.0
            if sec is None:
                factors["dyadStarvation"] = 1.2
            else:
                factors["dyadStarvation"] = 1.0
            factors["taskAffinity"] = (
                dyad_task_affinity_score(
                    a, b, tasks_by_char, scene_id=scene["sceneId"], half_life=half_life
                )
                if task_enabled
                else 0.0
            )
            factors["jitter"] = 1.0 + random.uniform(0, jitter_scale)
            total = (
                factors["pairAppetite"] * 0.32
                + factors["relationshipTension"] * 0.2
                + factors["recencyDecay"] * 0.2
                + factors["starvation"] * 0.15
                + factors["dyadStarvation"] * 0.1
                + factors["taskAffinity"] * task_weight
            ) * factors["jitter"]
            scores.append(DyadScore(a=a, b=b, total=total, factors=factors))
    return scores


def pick_idle_dyad(
    services: Any,
    *,
    world_id: str,
    scene: dict[str, Any],
    cast: list[str],
) -> DyadPick | None:
    if len(cast) < 2:
        return None
    cfg = get_idle_social_config(services.store, world_id)
    top_k = int(cfg.get("idleSocialTopK", 3))
    explore = float(cfg.get("idleSocialExplorationRate", 0.12))
    scores = score_idle_dyads(services, world_id=world_id, scene=scene, cast=cast)
    if not scores:
        return None
    exploration = random.random() < explore
    if exploration and len(scores) > top_k:
        ordered = sorted(scores, key=lambda s: s.total, reverse=True)
        tail = ordered[top_k:]
        pick_row = _weighted_lottery(tail, len(tail))
        explored = True
    else:
        pick_row = _weighted_lottery(scores, top_k)
        explored = False
    chars = {c["characterId"]: c for c in services.store.list_world_characters(world_id)}
    wa = _char_weight(chars.get(pick_row.a, {}), cfg, pick_row.a)
    wb = _char_weight(chars.get(pick_row.b, {}), cfg, pick_row.b)
    first = random.choices([pick_row.a, pick_row.b], weights=[wa, wb], k=1)[0]
    second = pick_row.b if first == pick_row.a else pick_row.a
    session_id = str(uuid.uuid4())
    tasks_by_char = collect_active_tasks_by_character(
        services, world_id=world_id, scene_id=scene["sceneId"]
    )
    task_hints = task_hints_for_characters(
        tasks_by_char, [pick_row.a, pick_row.b]
    )
    return DyadPick(
        speaking_order=[first, second],
        session_id=session_id,
        rationale={
            "pick": "idle_dyad",
            "dyad": [pick_row.a, pick_row.b],
            "exploration": explored,
            "scores": {
                dyad_key(s.a, s.b): {"total": s.total, **s.factors} for s in scores[:12]
            },
            "banterSessionId": session_id,
            "taskHints": task_hints,
        },
    )


def pick_banter_next_speaker(
    activity: dict[str, Any],
    *,
    last_speaker_id: str | None,
    services: Any,
    world_id: str,
) -> str | None:
    order = activity.get("speakingOrder") or []
    if len(order) < 2:
        return order[0] if order else None
    a, b = order[0], order[1]
    cfg = get_idle_social_config(services.store, world_id)
    chars = {c["characterId"]: c for c in services.store.list_world_characters(world_id)}
    wa = _char_weight(chars.get(a, {}), cfg, a)
    wb = _char_weight(chars.get(b, {}), cfg, b)
    if last_speaker_id == a:
        wa *= 0.35
    elif last_speaker_id == b:
        wb *= 0.35
    return random.choices([a, b], weights=[max(_MIN_SCORE, wa), max(_MIN_SCORE, wb)], k=1)[0]


def pick_idle_participant(
    services: Any,
    *,
    world_id: str,
    scene: dict[str, Any],
    cast: list[str],
) -> tuple[str | None, dict[str, Any]]:
    if not cast:
        return None, {}
    cfg = get_idle_social_config(services.store, world_id)
    half_life = float(cfg.get("idleSocialRecencyHalfLifeSeconds", 300))
    jitter_scale = float(cfg.get("idleSocialJitter", 0.15))
    chars = {c["characterId"]: c for c in services.store.list_world_characters(world_id)}
    last_speaker: str | None = None
    session_spoke: set[str] = set()
    for m in reversed(services.store.list_messages(world_id, scene_id=scene["sceneId"])):
        cid = m.get("characterId")
        if not cid or cid not in cast:
            continue
        try:
            import json

            meta = json.loads(m.get("metaJson") or "{}")
            trig = (meta.get("orchestration") or {}).get("trigger")
            if trig == "idle_timer":
                if last_speaker is None:
                    last_speaker = cid
                session_spoke.add(cid)
                if len(session_spoke) >= len(cast):
                    break
        except Exception:
            continue

    scored: list[tuple[str, float, dict[str, float]]] = []
    for cid in cast:
        ch = chars.get(cid, {})
        factors: dict[str, float] = {}
        factors["speechWeight"] = _char_weight(ch, cfg, cid)
        factors["recency"] = 0.35 if cid == last_speaker else 0.85
        factors["starvation"] = 1.15 if cid not in session_spoke else 0.75
        factors["jitter"] = 1.0 + random.uniform(0, jitter_scale)
        total = (
            factors["speechWeight"] * 0.5
            + factors["recency"] * 0.25
            + factors["starvation"] * 0.25
        ) * factors["jitter"]
        scored.append((cid, total, factors))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_k = min(3, len(scored))
    pool = scored[:top_k]
    weights = [max(_MIN_SCORE, s[1]) for s in pool]
    pick = random.choices(pool, weights=weights, k=1)[0]
    return pick[0], {
        "pick": "idle_participant",
        "characterId": pick[0],
        "scores": {cid: {"total": t, **f} for cid, t, f in scored},
    }
