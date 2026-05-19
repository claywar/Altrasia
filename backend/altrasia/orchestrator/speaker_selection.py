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

AddressingMode = Literal["directed", "ensemble", "open", "clarification"]
AddressingConfidence = Literal["high", "medium", "low"]

_VOCATIVE_START = re.compile(r"^@?([A-Za-z][\w'-]*)[,:]?\s", re.I)
_LONE_NAME = re.compile(r"^@?([A-Za-z][\w'-]{2,})\s*[?!.]?\s*$", re.I)
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
    confidence: AddressingConfidence = "high"
    match_reason: str = ""
    candidate_ids: list[str] = field(default_factory=list)
    clarifier_id: str | None = None
    absent_names: list[str] = field(default_factory=list)
    unresolved_name_tokens: list[str] = field(default_factory=list)


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


def _last_name(display: str) -> str:
    parts = display.split()
    return parts[-1].lower() if parts else ""


def _character_aliases(ch_row: dict) -> list[str]:
    defn: dict[str, Any] = {}
    raw_def = ch_row.get("definitionJson")
    if isinstance(raw_def, str) and raw_def.strip():
        try:
            defn = json.loads(raw_def)
        except json.JSONDecodeError:
            defn = {}
    elif isinstance(raw_def, dict):
        defn = dict(raw_def)
    fixture_def = ch_row.get("definition")
    if isinstance(fixture_def, dict):
        defn = {**defn, **fixture_def}
    inner = defn.get("definition")
    if isinstance(inner, dict):
        defn = {**defn, **inner}
    aliases = defn.get("aliases") or []
    if not isinstance(aliases, list):
        return []
    return [str(a).strip().lower() for a in aliases if a and str(a).strip()]


def _all_aliases(
    ch_row: dict | None,
    character_id: str,
    operator_alias_map: dict[str, list[str]] | None,
) -> list[str]:
    names = _character_aliases(ch_row) if ch_row else []
    if operator_alias_map:
        names = names + list(operator_alias_map.get(character_id, []))
    return names


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


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
        "confidence": result.confidence,
        "matchReason": result.match_reason,
        "candidateIds": list(result.candidate_ids),
        "clarifierId": result.clarifier_id,
        "absentNames": list(result.absent_names),
        "unresolvedNameTokens": list(result.unresolved_name_tokens),
    }


def addressing_from_dict(data: dict[str, Any] | None) -> AddressingResult | None:
    if not data or not isinstance(data, dict):
        return None
    mode = data.get("mode")
    if mode not in ("directed", "ensemble", "open", "clarification"):
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
    raw_candidates = data.get("candidateIds") or []
    if not isinstance(raw_candidates, list):
        raw_candidates = []
    conf = data.get("confidence") or "high"
    if conf not in ("high", "medium", "low"):
        conf = "high"
    return AddressingResult(
        mode=mode,
        primary_id=str(primary) if primary else (addressee_ids[0] if addressee_ids else None),
        addressee_ids=addressee_ids,
        eligible_continue=[str(c) for c in eligible],
        confidence=conf,
        match_reason=str(data.get("matchReason") or ""),
        candidate_ids=[str(c) for c in raw_candidates if c],
        clarifier_id=str(data["clarifierId"]) if data.get("clarifierId") else None,
        absent_names=[
            str(n) for n in (data.get("absentNames") or []) if n and str(n).strip()
        ],
        unresolved_name_tokens=[
            str(n)
            for n in (data.get("unresolvedNameTokens") or [])
            if n and str(n).strip()
        ],
    )


def _token_matches_character(
    token: str,
    character_id: str,
    display: str,
    ch_row: dict | None = None,
    operator_alias_map: dict[str, list[str]] | None = None,
) -> bool:
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
    if ch_row and t in _all_aliases(ch_row, character_id, operator_alias_map):
        return True
    return False


def _candidates_for_token_exact(
    token: str,
    cast: list[str],
    chars: dict[str, dict],
    operator_alias_map: dict[str, list[str]] | None = None,
) -> list[str]:
    matches: list[str] = []
    for cid in cast:
        ch_row = chars.get(cid, {})
        display = ch_row.get("displayName", "")
        if display and _token_matches_character(
            token, cid, display, ch_row, operator_alias_map
        ):
            matches.append(cid)
    return matches


def _candidate_for_unique_last_name(
    token: str, cast: list[str], chars: dict[str, dict]
) -> str | None:
    t = token.lower().strip()
    if len(t) < 2:
        return None
    matches: list[str] = []
    for cid in cast:
        display = chars.get(cid, {}).get("displayName", "")
        if display and _last_name(display) == t:
            matches.append(cid)
    if len(matches) == 1:
        return matches[0]
    return None


def _fuzzy_ranked_candidates(
    token: str,
    cast: list[str],
    chars: dict[str, dict],
    *,
    max_distance: int,
    operator_alias_map: dict[str, list[str]] | None = None,
) -> list[tuple[str, int]]:
    t = token.lower().strip()
    if len(t) < 4:
        return []
    limit = 1 if len(t) <= 5 else max_distance
    ranked: list[tuple[str, int]] = []
    for cid in cast:
        ch = chars.get(cid, {})
        display = ch.get("displayName", "")
        if not display:
            continue
        names = [
            _first_name(display),
            _last_name(display),
            _character_slug(cid),
            *_all_aliases(ch, cid, operator_alias_map),
        ]
        best = min(_levenshtein(t, n) for n in names if n)
        if best <= limit:
            ranked.append((cid, best))
    ranked.sort(key=lambda x: (x[1], x[0]))
    return ranked


def _resolve_token(
    token: str,
    cast: list[str],
    chars: dict[str, dict],
    *,
    fuzzy_enabled: bool,
    fuzzy_max_distance: int,
    operator_alias_map: dict[str, list[str]] | None = None,
) -> tuple[list[str], str, AddressingConfidence]:
    """Return (candidate_ids, match_reason, confidence) for one name token."""
    exact = _candidates_for_token_exact(token, cast, chars, operator_alias_map)
    if len(exact) == 1:
        return exact, "exact", "high"
    if len(exact) > 1:
        return exact, "ambiguous", "low"

    last = _candidate_for_unique_last_name(token, cast, chars)
    if last:
        return [last], "last_name", "high"

    if not fuzzy_enabled:
        return [], "none", "low"

    ranked = _fuzzy_ranked_candidates(
        token,
        cast,
        chars,
        max_distance=fuzzy_max_distance,
        operator_alias_map=operator_alias_map,
    )
    if not ranked:
        return [], "none", "low"
    best_dist = ranked[0][1]
    best = [cid for cid, d in ranked if d == best_dist]
    if len(best) == 1:
        conf: AddressingConfidence = "medium" if best_dist > 0 else "high"
        return best, "fuzzy" if best_dist > 0 else "exact", conf
    second_dist = ranked[len(best)][1] if len(ranked) > len(best) else best_dist + 2
    if second_dist - best_dist < 1:
        return best, "ambiguous", "low"
    return best, "ambiguous", "low"


def pick_clarifier(
    candidate_ids: list[str],
    chars: dict[str, dict],
    *,
    prefer_order: list[str] | None = None,
) -> str | None:
    if not candidate_ids:
        return None
    if prefer_order:
        for cid in prefer_order:
            if cid in candidate_ids:
                return cid
    return max(
        candidate_ids,
        key=lambda cid: float(chars.get(cid, {}).get("speechWeight", 0.5)),
    )


def resolve_directed_followup_reply(
    trigger_text: str,
    cast: list[str],
    chars: dict[str, dict],
    prior: AddressingResult,
    prior_operator_message_id: str,
    store: Any,
    world_id: str,
    scene_id: str,
    *,
    fuzzy_enabled: bool = True,
    fuzzy_max_distance: int = 2,
    operator_alias_map: dict[str, list[str]] | None = None,
) -> AddressingResult | None:
    """Short follow-up when a prior directed line still has addressees who have not spoken."""
    if prior.mode != "directed":
        return None
    addressees = addressee_ids_for(prior)
    spoke = set()
    if prior_operator_message_id:
        rows = store.conn.execute(
            """SELECT characterId FROM GenerationJob
               WHERE worldId = ? AND sceneId = ? AND triggerMessageId = ?
                 AND status = 'done' AND characterId IS NOT NULL""",
            (world_id, scene_id, prior_operator_message_id),
        ).fetchall()
        spoke = {row[0] for row in rows}
    missing = [cid for cid in addressees if cid not in spoke]
    stripped = trigger_text.strip().rstrip("?!.")
    if not stripped or len(stripped.split()) > 4:
        return None
    token = stripped.split()[0].lstrip("@")
    ids, reason, conf = _resolve_token(
        token,
        cast,
        chars,
        fuzzy_enabled=fuzzy_enabled,
        fuzzy_max_distance=fuzzy_max_distance,
        operator_alias_map=operator_alias_map,
    )
    target: str | None = None
    if len(ids) == 1:
        if ids[0] in missing:
            target = ids[0]
        elif ids[0] in cast and ids[0] not in spoke:
            target = ids[0]
    if not target and prior.unresolved_name_tokens:
        for unresolved in prior.unresolved_name_tokens:
            uids, _, _ = _resolve_token(
                unresolved,
                cast,
                chars,
                fuzzy_enabled=fuzzy_enabled,
                fuzzy_max_distance=fuzzy_max_distance,
                operator_alias_map=operator_alias_map,
            )
            if len(uids) == 1 and uids[0] not in spoke:
                target = uids[0]
                break
        if not target and token.lower() in {t.lower() for t in prior.unresolved_name_tokens}:
            uids, _, _ = _resolve_token(
                token,
                cast,
                chars,
                fuzzy_enabled=fuzzy_enabled,
                fuzzy_max_distance=fuzzy_max_distance,
                operator_alias_map=operator_alias_map,
            )
            if len(uids) == 1:
                target = uids[0]
    if not target:
        return None
    eligible = [c for c in cast if c != PERSONA_ID]
    witnesses = [c for c in eligible if c != target]
    return AddressingResult(
        mode="directed",
        primary_id=target,
        addressee_ids=[target],
        eligible_continue=witnesses,
        confidence=conf,
        match_reason="directed_followup",
    )


def resolve_clarification_reply(
    trigger_text: str,
    cast: list[str],
    chars: dict[str, dict],
    pending: AddressingResult,
    *,
    fuzzy_enabled: bool = True,
    fuzzy_max_distance: int = 2,
    operator_alias_map: dict[str, list[str]] | None = None,
) -> AddressingResult | None:
    """Resolve a short follow-up after clarification (e.g. operator says 'Lena')."""
    if pending.mode != "clarification":
        return None
    pool = [c for c in pending.candidate_ids if c in cast]
    if not pool:
        return None
    stripped = trigger_text.strip()
    if not stripped or len(stripped.split()) > 4:
        return None
    ids, reason, conf = _resolve_token(
        stripped.split()[0],
        cast,
        chars,
        fuzzy_enabled=fuzzy_enabled,
        fuzzy_max_distance=fuzzy_max_distance,
        operator_alias_map=operator_alias_map,
    )
    if len(ids) == 1 and ids[0] in pool:
        eligible = [c for c in cast if c != PERSONA_ID]
        witnesses = [c for c in eligible if c not in ids]
        return AddressingResult(
            mode="directed",
            primary_id=ids[0],
            addressee_ids=list(ids),
            eligible_continue=witnesses,
            confidence="high",
            match_reason="clarification_resolve",
        )
    return None


def _chars_for_present_cast(
    chars: dict[str, dict], cast: list[str]
) -> dict[str, dict]:
    """Character rows limited to who is present in the scene."""
    return {cid: chars[cid] for cid in cast if cid in chars}


def _operator_name_tokens(trigger_text: str) -> list[str]:
    """Name tokens the operator used to address someone (vocative or multi-addressee head)."""
    stripped = trigger_text.strip().rstrip("?!.")
    head = _MULTI_HEAD.match(stripped)
    if head:
        segment = head.group(1).strip().rstrip(",")
        if "," in segment or _NAME_JOIN.search(segment):
            return _name_tokens_from_segment(segment.replace(",", " and "))
    voc = _VOCATIVE_START.match(stripped)
    if voc:
        return [voc.group(1)]
    lone = _LONE_NAME.match(stripped)
    if lone:
        return [lone.group(1)]
    return []


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
    *,
    fuzzy_enabled: bool = True,
    fuzzy_max_distance: int = 2,
    operator_alias_map: dict[str, list[str]] | None = None,
) -> tuple[list[str], str, AddressingConfidence, list[str]]:
    """Returns (addressee_ids, match_reason, confidence, ambiguous_candidates)."""
    if target_character_id and target_character_id in cast:
        return [target_character_id], "explicit_target", "high", []
    stripped = trigger_text.strip().rstrip("?!.")
    head_match = _MULTI_HEAD.match(stripped)
    if head_match:
        segment = head_match.group(1).strip().rstrip(",")
        if _NAME_JOIN.search(segment) or "," in segment:
            resolved: list[str] = []
            reasons: list[str] = []
            conf: AddressingConfidence = "high"
            ambiguous: list[str] = []
            for token in _name_tokens_from_segment(segment.replace(",", " and ")):
                ids, reason, tok_conf = _resolve_token(
                    token,
                    cast,
                    chars,
                    fuzzy_enabled=fuzzy_enabled,
                    fuzzy_max_distance=fuzzy_max_distance,
                    operator_alias_map=operator_alias_map,
                )
                if reason == "ambiguous":
                    ambiguous.extend(ids)
                    conf = "low"
                    continue
                if len(ids) == 1 and ids[0] not in resolved:
                    resolved.append(ids[0])
                    reasons.append(reason)
                    if tok_conf == "medium":
                        conf = "medium"
            if ambiguous and not resolved:
                return [], "ambiguous", "low", list(dict.fromkeys(ambiguous))
            if len(resolved) == 1:
                return resolved, reasons[0] if reasons else "exact", conf, []
            if len(resolved) >= 2:
                return resolved, "multi_name", conf, []
    mention = re.search(r"@([\w-]+)", trigger_text, re.I)
    if mention:
        ids, reason, conf = _resolve_token(
            mention.group(1),
            cast,
            chars,
            fuzzy_enabled=fuzzy_enabled,
            fuzzy_max_distance=fuzzy_max_distance,
            operator_alias_map=operator_alias_map,
        )
        if len(ids) == 1:
            return ids, reason, conf, []
        if len(ids) > 1:
            return [], "ambiguous", "low", ids
    lower = trigger_text.lower()
    full_name_matches: list[str] = []
    for cid in cast:
        display = chars.get(cid, {}).get("displayName", "")
        if display and display.lower() in lower:
            full_name_matches.append(cid)
    if len(full_name_matches) == 1:
        return full_name_matches, "full_name", "high", []
    if len(full_name_matches) > 1:
        return [], "ambiguous", "low", full_name_matches
    vocative = _VOCATIVE_START.match(stripped)
    if vocative:
        ids, reason, conf = _resolve_token(
            vocative.group(1),
            cast,
            chars,
            fuzzy_enabled=fuzzy_enabled,
            fuzzy_max_distance=fuzzy_max_distance,
            operator_alias_map=operator_alias_map,
        )
        if len(ids) == 1:
            return ids, reason, conf, []
        if len(ids) > 1:
            return [], "ambiguous", "low", ids
    lone = _LONE_NAME.match(stripped)
    if lone:
        ids, reason, conf = _resolve_token(
            lone.group(1),
            cast,
            chars,
            fuzzy_enabled=fuzzy_enabled,
            fuzzy_max_distance=fuzzy_max_distance,
            operator_alias_map=operator_alias_map,
        )
        if len(ids) == 1:
            return ids, reason, conf, []
        if len(ids) > 1:
            return [], "ambiguous", "low", ids
    return [], "none", "low", []


def _parse_addressed(
    trigger_text: str,
    cast: list[str],
    chars: dict[str, dict],
    target_character_id: str | None = None,
    **kwargs: Any,
) -> str | None:
    ids, _, _, _ = _parse_addressed_list(
        trigger_text, cast, chars, target_character_id, **kwargs
    )
    return ids[0] if len(ids) == 1 else None


def parse_addressing(
    trigger_text: str,
    cast: list[str],
    chars: dict[str, dict],
    *,
    target_character_id: str | None = None,
    fuzzy_enabled: bool = True,
    fuzzy_max_distance: int = 2,
    pending_clarification: AddressingResult | None = None,
    operator_alias_map: dict[str, list[str]] | None = None,
) -> AddressingResult:
    """Classify operator intent: directed, multi, ensemble, open, or clarification."""
    eligible = [c for c in cast if c != PERSONA_ID]
    scene_chars = _chars_for_present_cast(chars, eligible)
    if pending_clarification:
        resolved = resolve_clarification_reply(
            trigger_text,
            eligible,
            scene_chars,
            pending_clarification,
            fuzzy_enabled=fuzzy_enabled,
            fuzzy_max_distance=fuzzy_max_distance,
            operator_alias_map=operator_alias_map,
        )
        if resolved:
            return resolved
    if trigger_invites_ensemble(trigger_text or ""):
        return AddressingResult(
            mode="ensemble",
            primary_id=None,
            eligible_continue=list(eligible),
            confidence="high",
            match_reason="ensemble_cue",
        )
    addressees, match_reason, confidence, ambiguous = _parse_addressed_list(
        trigger_text,
        eligible,
        scene_chars,
        target_character_id,
        fuzzy_enabled=fuzzy_enabled,
        fuzzy_max_distance=fuzzy_max_distance,
        operator_alias_map=operator_alias_map,
    )
    if ambiguous and not addressees:
        clarifier = pick_clarifier(ambiguous, scene_chars, prefer_order=ambiguous)
        return AddressingResult(
            mode="clarification",
            primary_id=None,
            addressee_ids=[],
            eligible_continue=eligible,
            confidence="low",
            match_reason="ambiguous",
            candidate_ids=list(dict.fromkeys(ambiguous)),
            clarifier_id=clarifier,
        )
    if addressees:
        witnesses = [c for c in eligible if c not in addressees]
        name_tokens = _operator_name_tokens(trigger_text)
        unresolved_tokens: list[str] = []
        if name_tokens:
            for token in name_tokens:
                ids, _, _ = _resolve_token(
                    token,
                    eligible,
                    scene_chars,
                    fuzzy_enabled=fuzzy_enabled,
                    fuzzy_max_distance=fuzzy_max_distance,
                    operator_alias_map=operator_alias_map,
                )
                if len(ids) == 1 and ids[0] in addressees:
                    continue
                unresolved_tokens.append(token)
        return AddressingResult(
            mode="directed",
            primary_id=addressees[0],
            addressee_ids=list(addressees),
            eligible_continue=witnesses,
            confidence=confidence,
            match_reason=match_reason,
            unresolved_name_tokens=list(dict.fromkeys(unresolved_tokens)),
        )
    name_tokens = _operator_name_tokens(trigger_text)
    if name_tokens and not addressees and not ambiguous:
        clarifier = pick_clarifier(eligible, scene_chars, prefer_order=eligible)
        return AddressingResult(
            mode="clarification",
            primary_id=None,
            addressee_ids=[],
            eligible_continue=list(eligible),
            confidence="low",
            match_reason="not_in_scene",
            candidate_ids=list(eligible),
            clarifier_id=clarifier,
            absent_names=list(dict.fromkeys(name_tokens)),
        )
    return AddressingResult(
        mode="open",
        primary_id=None,
        eligible_continue=list(eligible),
        confidence="low",
        match_reason="none",
    )


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


def _name_tokens_in_trigger(trigger_text: str) -> list[str]:
    """Name-like tokens from vocative, @mentions, multi-addressee head, and capitalized words."""
    stripped = trigger_text.strip()
    tokens: list[str] = []
    voc = _VOCATIVE_START.match(stripped)
    if voc:
        tokens.append(voc.group(1))
    for m in re.finditer(r"@([\w-]+)", trigger_text, re.I):
        tokens.append(m.group(1))
    head = _MULTI_HEAD.match(stripped)
    if head:
        tokens.extend(
            _name_tokens_from_segment(head.group(1).strip().rstrip(",").replace(",", " and "))
        )
    for m in re.finditer(r"\b([A-Z][a-z][\w'-]*)\b", trigger_text):
        tokens.append(m.group(1))
    return tokens


def _characters_named_in_trigger(
    trigger_text: str,
    cast: list[str],
    chars: dict[str, dict],
    *,
    fuzzy_enabled: bool = True,
    fuzzy_max_distance: int = 2,
    operator_alias_map: dict[str, list[str]] | None = None,
) -> set[str]:
    """Character ids explicitly named in the operator line."""
    named: set[str] = set()
    lower = trigger_text.lower()
    for cid in cast:
        display = chars.get(cid, {}).get("displayName", "")
        if display and display.lower() in lower:
            named.add(cid)
    for token in _name_tokens_in_trigger(trigger_text):
        ids, _, _ = _resolve_token(
            token,
            cast,
            chars,
            fuzzy_enabled=fuzzy_enabled,
            fuzzy_max_distance=fuzzy_max_distance,
            operator_alias_map=operator_alias_map,
        )
        if len(ids) == 1:
            named.add(ids[0])
    return named


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
    require_mention: bool = True,
    fuzzy_enabled: bool = True,
    fuzzy_max_distance: int = 2,
) -> SpeakerPick | None:
    """Best non-addressee witness if relevance meets threshold."""
    pool = [
        c
        for c in eligible
        if c not in exclude_ids and c != primary_id and c != PERSONA_ID
    ]
    if not pool:
        return None
    if require_mention:
        from altrasia.orchestrator.operator_aliases import operator_alias_map as _op_aliases

        op_map = _op_aliases(services.store, world_id)
        chars = {
            c["characterId"]: c
            for c in services.store.list_world_characters(world_id)
        }
        named = _characters_named_in_trigger(
            trigger_text,
            eligible,
            chars,
            fuzzy_enabled=fuzzy_enabled,
            fuzzy_max_distance=fuzzy_max_distance,
            operator_alias_map=op_map,
        )
        pool = [c for c in pool if c in named]
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
        fuzzy_enabled=fuzzy_enabled,
        fuzzy_max_distance=fuzzy_max_distance,
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
    fuzzy_enabled: bool = True,
    fuzzy_max_distance: int = 2,
) -> SpeakerPick | None:
    """AO-18: weighted speaker selection with AO-17 relevance."""
    blocked = set(exclude_ids or ())
    if exclude_id:
        blocked.add(exclude_id)
    cast = [c for c in eligible if c not in (PERSONA_ID,) and c not in blocked]
    if not cast:
        return None
    cast = cast[:8]
    all_chars = {
        c["characterId"]: c for c in services.store.list_world_characters(world_id)
    }
    scene_chars = _chars_for_present_cast(all_chars, cast)
    from altrasia.orchestrator.operator_aliases import operator_alias_map as _op_aliases

    op_map = _op_aliases(services.store, world_id)

    if not skip_addressed_override:
        addressed = _parse_addressed(
            trigger_text,
            cast,
            scene_chars,
            target_character_id,
            fuzzy_enabled=fuzzy_enabled,
            fuzzy_max_distance=fuzzy_max_distance,
            operator_alias_map=op_map,
        )
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
        ch = scene_chars.get(cid, {})
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
