from __future__ import annotations

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.money import ZERO


class Job(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    TRANSITIONS = {
        Status.PENDING: {Status.IN_PROGRESS, Status.CANCELLED, Status.COMPLETED},
        Status.IN_PROGRESS: {Status.COMPLETED, Status.CANCELLED},
        Status.COMPLETED: set(),
        Status.CANCELLED: set(),
    }

    creator = models.ForeignKey(
        "creators.Creator", on_delete=models.PROTECT, related_name="jobs"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    base_amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(ZERO)]
    )
    surge_multiplier = models.DecimalField(
        max_digits=5, decimal_places=2, default=1.00,
        validators=[MinValueValidator(1.00)],
        help_text="Applied to base_amount before tips (e.g. 1.50).",
    )
    tip_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=ZERO, validators=[MinValueValidator(ZERO)]
    )
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jobs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["creator", "status"], name="job_creator_status_idx"),
            models.Index(fields=["status", "completed_at"], name="job_status_completed_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(base_amount__gte=0),
                name="job_base_amount_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(tip_amount__gte=0),
                name="job_tip_amount_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(surge_multiplier__gte=1),
                name="job_surge_multiplier_at_least_one",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.status})"
