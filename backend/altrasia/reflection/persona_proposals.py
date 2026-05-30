from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

ISO = lambda: datetime.now(timezone.utc).isoformat()


def approve_persona_proposal(svc: Any, proposal_id: str) -> dict[str, Any]:
    prop = svc.store.get_persona_proposal(proposal_id)
    if not prop:
        raise ValueError("proposal not found")
    if prop.get("status") != "pending":
        raise ValueError("proposal already resolved")

    ch = svc.store.get_character(prop["characterId"])
    if not ch:
        raise ValueError("character not found")

    try:
        definition = json.loads(ch.get("definitionJson") or "{}")
    except json.JSONDecodeError:
        definition = {}

    field = prop["field"]
    proposed = prop["proposedValue"]
    if field == "focusTags":
        try:
            tags = json.loads(proposed) if proposed.startswith("[") else [proposed]
            definition["focusTags"] = tags if isinstance(tags, list) else [str(proposed)]
        except json.JSONDecodeError:
            definition["focusTags"] = [t.strip() for t in proposed.split(",") if t.strip()]
    else:
        definition[field] = proposed

    svc.store.update_character(
        prop["characterId"],
        definitionJson=json.dumps(definition),
    )
    svc.store.update_persona_proposal(
        proposal_id,
        status="approved",
        resolvedAt=ISO(),
    )
    from altrasia.evidence import record_evidence

    record_evidence(
        svc.store,
        locus_key=f"persona:{field}",
        pool="mind",
        owner_id=prop["characterId"],
        source_kind="reflection",
        source_ref=prop.get("reflectionRunId") or proposal_id,
    )
    return {
        "proposalId": proposal_id,
        "status": "approved",
        "characterId": prop["characterId"],
        "definition": definition,
    }


def reject_persona_proposal(svc: Any, proposal_id: str) -> dict[str, Any]:
    prop = svc.store.get_persona_proposal(proposal_id)
    if not prop:
        raise ValueError("proposal not found")
    if prop.get("status") != "pending":
        raise ValueError("proposal already resolved")
    svc.store.update_persona_proposal(
        proposal_id,
        status="rejected",
        resolvedAt=ISO(),
    )
    return {"proposalId": proposal_id, "status": "rejected"}
