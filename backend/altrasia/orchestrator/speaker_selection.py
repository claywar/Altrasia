from __future__ import annotations

import hashlib
import json
import random
import re
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from altrasia.domain.presence import PERSONA_ID
from altrasia.orchestrator.single_speaker import trigger_invites_ensemble

_SCORE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL = 30.0
_TIE_EPSILON = 0.05

AddressingMode = Literal["directed", "ensemble", "open"]

_VOCATIVE_START = re.compile(r"^@?([A-Za-z][\w'-]*)[,:]?\s", re.I)
_NAME_JOIN = re.compile(r"\s+(?:and|&)\s+", re.I)
_MULTI_HEAD = re.compile(
    r"^(.+?)(?:,\s*|\s+)"
    r"(?=(?:what|who|where|when|how|why|tell|describe|explain|are|is|do|can)\b)",
    re.I,
)


@dataclass
class SpeakerPick:
    character_id: str
    rationale: dict[str, Any]


@dataclass
class AddressingResult:
    mode: AddressingMode
    primary_id: str | None = None
    addressee_ids: list[str] = field(default_factory=list)
    eligible_continue: list[str] = field(default_factory=list)


@dataclass
class _CharScore:
    character_id: str
    total: float
    factors: dict[str, float] = field(default_factory=dict)


def _cache_key(scene_id: str, trigger_message_id: str | None, eligible: list[str]) -> str:
    h = hashlib.sha256(",".join(sorted(eligible)).encode()).hexdigest()[:16]
    return f"{scene_id}:{trigger_message_id or 'none'}:{h}"


def _character_slug(character_id: str) -> str:
    if character_id.startswith("char-"):
        return character_id[5:].lower()
    return character_id.lower()


def _first_name(display: str) -> str:
    return (display.split() or [""])[0].lower()


def addressee_ids_for(addressing: AddressingResult | None) -> list[str]:
    if not addressing:
        return []
    if addressing.addressee_ids:
        return list(addressing.addressee_ids)
    if addressing.primary_id:
        return [addressing.primary_id]
    return []


def is_multi_directed(addressing: AddressingResult | None) -> bool:
    return len(addressee_ids_for(addressing)) > 1


def addressing_to_dict(result: AddressingResult) -> dict[str, Any]:
    ids = addressee_ids_for(result)
    return {
        "mode": result.mode,
        "primaryId": result.primary_id or (ids[0] if ids else None),
        "addresseeIds": ids,
        "eligibleContinue": list(result.eligible_continue),
    }


def addressing_from_dict(data: dict[str, Any] | None) -> AddressingResult | None:
    if not data or not isinstance(data, dict):
        return None
    mode = data.get("mode")
    if mode not in ("directed", "ensemble", "open"):
        return None
    primary = data.get("primaryId")
    raw_ids = data.get("addresseeIds") or []
    if not isinstance(raw_ids, list):
        raw_ids = []
    addressee_ids = [str(c) for c in raw_ids if c]
    if not addressee_ids and primary:
        addressee_ids = [str(primary)]
    eligible = data.get("eligibleContinue") or []
    if not isinstance(eligible, list):
        eligible = []
    return AddressingResult(
        mode=mode,
        primary_id=str(primary) if primary else (addressee_ids[0] if addressee_ids else None),
        addressee_ids=addressee_ids,
        eligible_continue=[str(c) for c in eligible],
    )


def _token_matches_character(token: str, character_id: str, display: str) -> bool:
    t = token.lower().strip()
    if not t:
        return False
    slug = _character_slug(character_id)
    first = _first_name(display)
    display_lower = display.lower()
    if t == first or t == slug:
        return True
    if t.replace("-", "") == first.replace("-", ""):
        return True
    if t in slug or slug.startswith(t + "-"):
        return True
    if display_lower and t in display_lower.split():
        return True
    return False


def _candidates_for_token(
    token: str, cast: list[str], chars: dict[str, dict]
) -> list[str]:
    matches: list[str] = []
    for cid in cast:
        display = chars.get(cid, {}).get("displayName", "")
        if display and _token_matches_character(token, cid, display):
            matches.append(cid)
    return matches


def _name_tokens_from_segment(segment: str) -> list[str]:
    tokens: list[str] = []
    for part in _NAME_JOIN.split(segment):
        part = part.strip().strip(",")
        if not part:
            continue
        match = re.match(r"([A-Za-z][\w'-]*)", part)
        if match:
            tokens.append(match.group(1))
    return tokens


def _parse_addressed_list(
    trigger_text: str,
    cast: list[str],
    chars: dict[str, dict],
    target_character_id: str | None = None,
) -> list[str]:
    """All explicitly named addressees in operator text (order preserved)."""
    if target_character_id and target_character_id in cast:
        return [target_character_id]
    stripped = trigger_text.strip()
    head_match = _MULTI_HEAD.match(stripped)
    if head_match:
        segment = head_match.group(1).strip().rstrip(",")
        if _NAME_JOIN.search(segment) or "," in segment:
            resolved: list[str] = []
            for token in _name_tokens_from_segment(segment.replace(",", " and ")):
                matches = _candidates_for_token(token, cast, chars)
                if len(matches) == 1 and matches[0] not in resolved:
                    resolved.append(matches[0])
            if len(resolved) >= 2:
                return resolved
    single = _parse_addressed(trigger_text, cast, chars, target_character_id)
    return [single] if single else []


def _parse_addressed(
    trigger_text: str,
    cast: list[str],
    chars: dict[str, dict],
    target_character_id: str | None = None,
) -> str | None:
    if target_character_id and target_character_id in cast:
        return target_character_id
    mention = re.search(r"@([\w-]+)", trigger_text, re.I)
    if mention:
        name = mention.group(1).lower()
        matches = _candidates_for_token(name, cast, chars)
        if len(matches) == 1:
            return matches[0]
    lower = trigger_text.lower()
    full_name_matches: list[str] = []
    for cid in cast:
        display = chars.get(cid, {}).get("displayName", "")
        if display and display.lower() in lower:
            full_name_matches.append(cid)
    if len(full_name_matches) == 1:
        return full_name_matches[0]
    stripped = trigger_text.strip()
    vocative = _VOCATIVE_START.match(stripped)
    if vocative:
        matches = _candidates_for_token(vocative.group(1), cast, chars)
        if len(matches) == 1:
            return matches[0]
    return None


def parse_addressing(
    trigger_text: str,
    cast: list[str],
    chars: dict[str, dict],
    *,
    target_character_id: str | None = None,
) -> AddressingResult:
    """Classify operator intent: directed (one or more addressees), ensemble, or open."""
    eligible = [c for c in cast if c != PERSONA_ID]
    if trigger_invites_ensemble(trigger_text or ""):
        return AddressingResult(
            mode="ensemble",
            primary_id=None,
            eligible_continue=list(eligible),
        )
    addressees = _parse_addressed_list(
        trigger_text, eligible, chars, target_character_id
    )
    if addressees:
        witnesses = [c for c in eligible if c not in addressees]
        return AddressingResult(
            mode="directed",
            primary_id=addressees[0],
            addressee_ids=list(addressees),
            eligible_continue=witnesses,
        )
    return AddressingResult(mode="open", primary_id=None, eligible_continue=list(eligible))


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


def pick_directed_witness(
    services: Any,
    *,
    world_id: str,
    scene_id: str,
    trigger_text: str,
    primary_id: str,
    eligible: list[str],
    exclude_ids: set[str],
    trigger_message_id: str | None,
    relevance_min: float,
) -> SpeakerPick | None:
    """Best non-addressee witness if relevance meets threshold."""
    pool = [
        c
        for c in eligible
        if c not in exclude_ids and c != primary_id and c != PERSONA_ID
    ]
    if not pool:
        return None
    pick = score_speakers(
        services,
        world_id=world_id,
        scene_id=scene_id,
        trigger_text=trigger_text,
        eligible=pool,
        exclude_ids=exclude_ids,
        trigger_message_id=trigger_message_id,
        skip_addressed_override=True,
    )
    if not pick:
        return None
    rel = float((pick.rationale.get("scores") or {}).get(pick.character_id, {}).get("relevance", 0))
    if rel < relevance_min:
        return None
    pick.rationale["pick"] = "directed_witness"
    return pick


def score_speakers(
    services: Any,
    *,
    world_id: str,
    scene_id: str,
    trigger_text: str,
    eligible: list[str],
    exclude_id: str | None = None,
    exclude_ids: set[str] | None = None,
    target_character_id: str | None = None,
    trigger_message_id: str | None = None,
    last_speaker_id: str | None = None,
    session_spoke: set[str] | None = None,
    skip_addressed_override: bool = False,
) -> SpeakerPick | None:
    """AO-18: weighted speaker selection with AO-17 relevance."""
    blocked = set(exclude_ids or ())
    if exclude_id:
        blocked.add(exclude_id)
    cast = [c for c in eligible if c not in (PERSONA_ID,) and c not in blocked]
    if not cast:
        return None
    cast = cast[:8]
    chars = {c["characterId"]: c for c in services.store.list_world_characters(world_id)}

    if not skip_addressed_override:
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
