from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.fields import DateTimeField
from rest_framework.response import Response

from apps.accounts.models import User
from apps.audit.services import AuditAction, record_audit
from apps.core.exceptions import UnauthorizedAccess, ValidationError
from apps.core.permissions import IsAdminOrSelf

from .filters import JobFilter
from .models import Job
from .serializers import JobSerializer, JobUpdateSerializer
from .services import complete_job


class JobViewSet(viewsets.ModelViewSet):
    serializer_class = JobSerializer
    permission_classes = [IsAdminOrSelf]
    filterset_class = JobFilter
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "completed_at", "base_amount"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    queryset = Job.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Job.objects.none()
        qs = Job.objects.select_related("creator", "creator__user", "earning")
        if self.request.user.role == User.Role.CREATOR:
            profile = getattr(self.request.user, "creator_profile", None)
            qs = qs.filter(creator=profile) if profile else qs.none()
        return qs

    def get_serializer_class(self):
        if self.action in {"partial_update", "update"}:
            return JobUpdateSerializer
        return JobSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role != User.Role.ADMIN:
            raise UnauthorizedAccess("Only admins can create jobs.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save()
        record_audit(request.user, AuditAction.JOB_CREATED, "Job", job.id,
                     metadata={"title": job.title, "base_amount": job.base_amount})
        return Response(JobSerializer(job, context=self.get_serializer_context()).data,
                        status=201)

    def partial_update(self, request, *args, **kwargs):
        if request.user.role != User.Role.ADMIN:
            raise UnauthorizedAccess("Only admins can modify jobs.")
        job: Job = self.get_object()
        serializer = JobUpdateSerializer(job, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        validated = dict(serializer.validated_data)
        use_service = validated.pop("_complete_via_service", False)
        new_status = validated.pop("status", None)

        with transaction.atomic():
            if use_service or new_status == Job.Status.COMPLETED:
                if validated:
                    for field, value in validated.items():
                        setattr(job, field, value)
                    job.save(update_fields=[*validated.keys(), "updated_at"])
                job = complete_job(job=job, actor=request.user)
            else:
                if new_status:
                    if new_status == Job.Status.CANCELLED and job.status != new_status:
                        job.status = new_status
                        validated.pop("status", None)
                    else:
                        job.status = new_status
                for field, value in validated.items():
                    setattr(job, field, value)
                job.save()
        record_audit(request.user, AuditAction.JOB_UPDATED, "Job", job.id,
                     metadata={"fields": sorted(request.data.keys())})
        return Response(JobSerializer(job, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """POST /api/jobs/:id/complete/ — completes the job and calculates earnings."""
        if request.user.role != User.Role.ADMIN:
            raise UnauthorizedAccess("Only admins can complete jobs.")
        job = self.get_object()
        completed_at = None
        if raw := request.data.get("completed_at"):
            completed_at = DateTimeField().to_internal_value(raw)
            if completed_at > timezone.now():
                raise ValidationError("completed_at cannot be in the future.")
        job = complete_job(job=job, actor=request.user, completed_at=completed_at)
        return Response(JobSerializer(job, context=self.get_serializer_context()).data)
