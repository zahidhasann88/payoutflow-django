from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from django.db.models import Model

from .models import AuditLog

logger = logging.getLogger("payoutflow.audit")


class AuditAction:
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    USER_UPDATED = "USER_UPDATED"
    CREATOR_CREATED = "CREATOR_CREATED"
    CREATOR_UPDATED = "CREATOR_UPDATED"
    JOB_CREATED = "JOB_CREATED"
    JOB_UPDATED = "JOB_UPDATED"
    JOB_COMPLETED = "JOB_COMPLETED"
    PAYOUT_RULE_CHANGED = "PAYOUT_RULE_CHANGED"
    PAYOUT_BATCH_CREATED = "PAYOUT_BATCH_CREATED"
    PAYOUT_BATCH_PROCESSED = "PAYOUT_BATCH_PROCESSED"
    PAYOUT_FAILED = "PAYOUT_FAILED"
    ADJUSTMENT_CREATED = "ADJUSTMENT_CREATED"


_SENSITIVE_KEYS = (
    "password", "token", "secret", "authorization", "credential",
    "jwt", "access", "refresh",
)
_MASKED_KEYS = ("payout_account", "phone")


def sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Strip secret-like keys and mask sensitive profile values."""
    clean: dict[str, Any] = {}
    for key, value in (metadata or {}).items():
        lowered = key.lower()
        if any(s in lowered for s in _SENSITIVE_KEYS):
            continue
        if any(s in lowered for s in _MASKED_KEYS) and isinstance(value, str) and value:
            clean[key] = f"***{value[-4:]}" if len(value) > 4 else "****"
            continue
        if isinstance(value, Decimal):
            clean[key] = str(value)
        elif isinstance(value, Model):
            clean[key] = str(value.pk)
        else:
            clean[key] = value
    return clean


def record_audit(
    user,
    action: str,
    entity_type: str = "",
    entity_id: str | int | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Persist an audit event. Never raises — auditing must not break flows."""
    try:
        return AuditLog.objects.create(
            user=user if getattr(user, "is_authenticated", False) else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else "",
            metadata=sanitize_metadata(metadata),
        )
    except Exception:
        logger.exception("Failed to record audit event %s", action)
        return None
