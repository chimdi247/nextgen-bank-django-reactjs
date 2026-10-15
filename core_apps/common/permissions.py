from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import View


def _has_role(request: Request, role: str) -> bool:
    """A branch manager supervises every other staff role, so managers (and superusers) pass all staff checks."""
    user = request.user
    if not (user and user.is_authenticated and hasattr(user, "role")):
        return False
    return user.role in (role, "branch_manager") or user.is_superuser


class IsAccountExecutive(permissions.BasePermission):
    def has_permission(self, request: Request, view: View) -> bool:
        return _has_role(request, "account_executive")


class IsTeller(permissions.BasePermission):
    def has_permission(self, request: Request, view: View) -> bool:
        return _has_role(request, "teller")


class IsBranchManager(permissions.BasePermission):
    def has_permission(self, request: Request, view: View) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and (getattr(user, "role", None) == "branch_manager" or user.is_superuser))
