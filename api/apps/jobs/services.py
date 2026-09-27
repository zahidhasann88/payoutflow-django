from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.audit.services import AuditAction, record_audit
from apps.core.error_codes import ErrorCode
from apps.core.exceptions import InvalidStatusTransition
from apps.earnings.services import create_earning_for_completed_job

from .models import Job


def complete_job(*, job: Job, actor, completed_at=None) -> Job:
    """
    Mark a job COMPLETED and create its earning in a single transaction.

    * COMPLETED/CANCELLED jobs cannot transition again.
    * An earning is created exactly once per job (unique constraint).
    """
    if job.status == Job.Status.COMPLETED:
        raise InvalidStatusTransition(
            "Job is already completed.",
            code=ErrorCode.INVALID_STATUS_TRANSITION,
        )
    if job.status == Job.Status.CANCELLED:
        raise InvalidStatusTransition(
            "A cancelled job cannot be completed.",
            code=ErrorCode.INVALID_STATUS_TRANSITION,
        )

    with transaction.atomic():
        locked = Job.objects.select_for_update().get(pk=job.pk)
        if locked.status == Job.Status.COMPLETED:
            raise InvalidStatusTransition("Job is already completed.")
        locked.status = Job.Status.COMPLETED
        locked.completed_at = completed_at or timezone.now()
        locked.save(update_fields=["status", "completed_at", "updated_at"])
        create_earning_for_completed_job(locked, actor=actor)
        record_audit(actor, AuditAction.JOB_COMPLETED, "Job", locked.id,
                     metadata={"title": locked.title,
                               "completed_at": locked.completed_at.isoformat()})
        return locked


def validate_status_transition(current: str, target: str) -> None:
    if current == target:
        return
    if target not in Job.TRANSITIONS.get(current, set()):
        raise InvalidStatusTransition(
            f"Cannot change job status from {current} to {target}.",
            code=ErrorCode.INVALID_STATUS_TRANSITION,
        )
