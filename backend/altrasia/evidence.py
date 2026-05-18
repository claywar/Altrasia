from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from altrasia.persistence.sqlite_store import SqlitePersistence

ISO = lambda: datetime.now(timezone.utc).isoformat()


def record_evidence(
    store: SqlitePersistence,
    *,
    locus_key: str,
    pool: str,
    owner_id: str,
    source_kind: str,
    source_ref: str,
    commission_id: str | None = None,
) -> dict[str, str]:
    """MP-21: link external or commission facts to a mind/world locus."""
    evidence_id = str(uuid.uuid4())
    store.insert_evidence(
        {
            "evidenceId": evidence_id,
            "locusKey": locus_key,
            "pool": pool,
            "ownerId": owner_id,
            "sourceKind": source_kind,
            "sourceRef": source_ref[:2000],
            "retrievedAt": ISO(),
            "commissionId": commission_id,
        }
    )
    return {"evidenceId": evidence_id, "locusKey": locus_key}
