from rest_framework.permissions import BasePermission

from rides.models import User


class HasAdminRole(BasePermission):
    message = "Only users with the admin role can access this endpoint."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user and request.user.is_authenticated and request.user.role == User.Role.ADMIN
        )
