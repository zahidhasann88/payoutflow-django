from __future__ import annotations

from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import AuditAction, record_audit

from .models import Creator


@transaction.atomic
def create_creator(*, actor: User, email: str, name: str, password: str,
                   profile_fields: dict) -> Creator:
    user = User.objects.create_user(email=email, password=password, name=name,
                                    role=User.Role.CREATOR)
    creator = Creator.objects.create(user=user, **profile_fields)
    record_audit(actor, AuditAction.CREATOR_CREATED, "Creator", creator.id,
                 metadata={"email": email, "display_name": creator.display_name})
    return creator


@transaction.atomic
def update_creator(*, actor: User, creator: Creator, profile_fields: dict,
                   user_fields: dict | None = None) -> Creator:
    if user_fields:
        for field, value in user_fields.items():
            setattr(creator.user, field, value)
        creator.user.save(update_fields=[*user_fields.keys(), "updated_at"])
    for field, value in profile_fields.items():
        setattr(creator, field, value)
    creator.save(update_fields=[*profile_fields.keys(), "updated_at"])
    record_audit(actor, AuditAction.CREATOR_UPDATED, "Creator", creator.id,
                 metadata={"fields": sorted(set(profile_fields) | set(user_fields or {}))})
    return creator
