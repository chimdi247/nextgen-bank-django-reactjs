import pytest
from rest_framework.test import APIRequestFactory

from core_apps.common.permissions import IsAccountExecutive, IsBranchManager, IsTeller
from tests.conftest import make_user

pytestmark = pytest.mark.django_db


def request_for(user):
    request = APIRequestFactory().get("/")
    request.user = user
    return request


@pytest.mark.parametrize("role,teller,executive,manager", [
    ("customer", False, False, False),
    ("teller", True, False, False),
    ("account_executive", False, True, False),
    ("branch_manager", True, True, True),      # a branch manager supervises every staff role
])
def test_role_matrix(role, teller, executive, manager):
    request = request_for(make_user(role))
    assert IsTeller().has_permission(request, None) is teller
    assert IsAccountExecutive().has_permission(request, None) is executive
    assert IsBranchManager().has_permission(request, None) is manager


def test_superuser_passes_every_staff_check():
    user = make_user("customer")
    user.is_superuser = True
    request = request_for(user)
    assert IsTeller().has_permission(request, None) and IsBranchManager().has_permission(request, None)


def test_anonymous_has_no_staff_permission():
    from django.contrib.auth.models import AnonymousUser

    request = request_for(AnonymousUser())
    assert not IsTeller().has_permission(request, None)
