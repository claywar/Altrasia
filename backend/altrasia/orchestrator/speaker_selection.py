from __future__ import annotations

import hashlib
import json
import random
import re
import time
from dataclasses import dataclass, field
from typing import Any

from altrasia.domain.presence import PERSONA_ID

_SCORE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL = 30.0
_TIE_EPSILON = 0.05


@dataclass
class SpeakerPick:
    character_id: str
    rationale: dict[str, Any]


@dataclass
class _CharScore:
    character_id: str
    total: float
    factors: dict[str, float] = field(default_factory=dict)


def _cache_key(scene_id: str, trigger_message_id: str | None, eligible: list[str]) -> str:
    h = hashlib.sha256(",".join(sorted(eligible)).encode()).hexdigest()[:16]
    return f"{scene_id}:{trigger_message_id or 'none'}:{h}"


def _parse_addressed(
    trigger_text: str,
    cast: list[str],
    chars: dict[str, dict],
    target_character_id: str | None = None,
) -> str | None:
    if target_character_id and target_character_id in cast:
        return target_character_id
    mention = re.search(r"@(\w+)", trigger_text, re.I)
    if mention:
        name = mention.group(1).lower()
        for cid in cast:
            display = chars.get(cid, {}).get("displayName", "")
            if display and name in display.lower():
                return cid
    lower = trigger_text.lower()
    for cid in cast:
        display = chars.get(cid, {}).get("displayName", "")
        if display and display.lower() in lower:
            return cid
    return None


def speak_readiness_score(
    memory: Any,
    character_id: str,
    trigger_text: str,
) -> float:
    """AO-17: one bounded FTS probe per character (mind + diary)."""
    query = " ".join(trigger_text.split()[:12]) or trigger_text[:80]
    if not query.strip():
        return 0.0
    mind = memory.memory_search(pool="mind", owner_id=character_id, query=query, limit=3)
    diary = memory.diary_search(character_id=character_id, query=query, limit=3)
    score = 0.0
    if mind:
        score += 0.35 + min(0.25, len(mind) * 0.08)
    if diary:
        score += 0.2 + min(0.2, len(diary) * 0.06)
    return min(1.0, score)


def score_speakers(
    services: Any,
    *,
    world_id: str,
    scene_id: str,
    trigger_text: str,
    eligible: list[str],
    exclude_id: str | None = None,
    target_character_id: str | None = None,
    trigger_message_id: str | None = None,
    last_speaker_id: str | None = None,
    session_spoke: set[str] | None = None,
) -> SpeakerPick | None:
    """AO-18: weighted speaker selection with AO-17 relevance."""
    cast = [c for c in eligible if c not in (PERSONA_ID, exclude_id)]
    if not cast:
        return None
    cast = cast[:8]
    chars = {c["characterId"]: c for c in services.store.list_world_characters(world_id)}

    addressed = _parse_addressed(trigger_text, cast, chars, target_character_id)
    if addressed:
        return SpeakerPick(
            character_id=addressed,
            rationale={
                "pick": "addressed",
                "characterId": addressed,
                "scores": {addressed: {"total": 1.0, "addressed": 1.0}},
            },
        )

    ck = _cache_key(scene_id, trigger_message_id, cast)
    now = time.monotonic()
    cached = _SCORE_CACHE.get(ck)
    if cached and now - cached[0] < _CACHE_TTL:
        return SpeakerPick(character_id=cached[1]["characterId"], rationale=cached[1])

    scores: list[_CharScore] = []
    for cid in cast:
        ch = chars.get(cid, {})
        factors: dict[str, float] = {}
        factors["speechWeight"] = float(ch.get("speechWeight", 0.5))
        factors["relevance"] = speak_readiness_score(services.memory, cid, trigger_text)
        emb_svc = getattr(services, "embeddings", None)
        if emb_svc and emb_svc.enabled:
            try:
                from altrasia.memory.embeddings import _hash_embed, cosine_similarity, vector_from_blob

                row = services.store.conn.execute(
                    """SELECT vectorBlob FROM EmbeddingRecord
                       WHERE ownerScope = 'mind' AND sourceId LIKE ? LIMIT 1""",
                    (f"{cid}:%",),
                ).fetchone()
                vec = vector_from_blob(row[0] if row else None)
                qvec = _hash_embed(trigger_text[:500])
                if vec and len(vec) == len(qvec):
                    sim = cosine_similarity(vec, qvec)
                    factors["embedRerank"] = round(min(0.3, max(0.0, sim) * 0.3), 4)
                    factors["relevance"] = min(1.0, factors["relevance"] + factors["embedRerank"])
            except Exception:
                pass
        role = ch.get("sceneRole")
        if role == "teacher" and "?" in trigger_text:
            factors["roleFit"] = 0.3
        elif role == "student" and "?" in trigger_text:
            factors["roleFit"] = 0.85
        else:
            factors["roleFit"] = 0.55
        if last_speaker_id and cid == last_speaker_id:
            factors["recencyPenalty"] = 0.15
        else:
            factors["recencyPenalty"] = 0.7
        if session_spoke and cid not in session_spoke:
            factors["starvation"] = 0.9
        else:
            factors["starvation"] = 0.5
        if last_speaker_id and cid != last_speaker_id:
            factors["dyadBoost"] = 0.75
        else:
            factors["dyadBoost"] = 0.4
        total = (
            factors["speechWeight"] * 0.25
            + factors["relevance"] * 0.35
            + factors["roleFit"] * 0.15
            + factors["recencyPenalty"] * 0.1
            + factors["starvation"] * 0.08
            + factors["dyadBoost"] * 0.07
        )
        scores.append(_CharScore(character_id=cid, total=total, factors=factors))

    scores.sort(key=lambda s: s.total, reverse=True)
    top = scores[0].total
    tied = [s for s in scores if top - s.total <= _TIE_EPSILON]
    if len(tied) > 1:
        pick_row = random.choice(tied)
    else:
        pick_row = scores[0]

    rationale = {
        "pick": "scoreSpeakers",
        "characterId": pick_row.character_id,
        "scores": {
            s.character_id: {"total": round(s.total, 4), **s.factors} for s in scores
        },
    }
    _SCORE_CACHE[ck] = (now, rationale)
    return SpeakerPick(character_id=pick_row.character_id, rationale=rationale)


async def resolve_speak_intent_tie(
    llm: Any,
    *,
    trigger_text: str,
    tied: list[str],
    chars: dict[str, dict],
) -> str | None:
    """v1.1: optional LLM batch pick when scores tie."""
    names = [chars.get(c, {}).get("displayName", c) for c in tied]
    prompt = (
        "Who should speak next in this scene? Reply with exactly one name from the list.\n"
        f"Line: {trigger_text[:500]}\n"
        f"Candidates: {', '.join(names)}"
    )
    resp = await llm.chat([{"role": "user", "content": prompt}], None)
    content = (resp.get("choices") or [{}])[0].get("message", {}).get("content", "")
    lower = content.lower()
    for cid in tied:
        display = chars.get(cid, {}).get("displayName", "")
        if display and display.lower() in lower:
            return cid
    return tied[0] if tied else None
