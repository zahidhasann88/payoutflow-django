from __future__ import annotations

from rest_framework.permissions import BasePermission

from apps.accounts.models import User


class IsAdmin(BasePermission):
    """Allow access only to users with the ADMIN role."""

    message = "Admin access is required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role == User.Role.ADMIN
            and user.status == User.Status.ACTIVE
        )


class IsActiveUser(BasePermission):
    """Any authenticated, non-suspended user."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.status == User.Status.ACTIVE
        )


class IsAdminOrSelf(BasePermission):
    """
    Admins can access everything; creators can access their own resources.

    Object-level checks consult ``obj.creator`` (Job/Earning/Payout) or
    ``obj.user`` (Creator profile). The queryset in each view is *also*
    scoped, so creators can never even enumerate other creators' rows —
    isolation is enforced by the backend, not the frontend.
    """

    message = "You cannot access another creator's data."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.status == User.Status.ACTIVE)

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if user.role == User.Role.ADMIN:
            return True
        creator = getattr(obj, "creator", None)
        if creator is not None:
            return getattr(user, "creator_profile", None) == creator
        owner = getattr(obj, "user", None)
        if owner is not None:
            return owner == user
        return False
