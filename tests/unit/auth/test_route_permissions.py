from collections.abc import Iterator
from typing import Any, Protocol

from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

try:
    from fastapi.routing import iter_route_contexts
except ImportError:

    def iter_route_contexts(routes: list[Any]) -> Iterator[Any]:
        return iter(routes)


from app.auth.rbac import Permission, PermissionChecker
from app.main import create_app

PUBLIC = None

EXPECTED_ROUTE_PERMISSIONS: dict[
    tuple[str, str],
    Permission | None,
] = {
    # Applications
    ("POST", "/applications/"): Permission.APPLICATION_CREATE,
    (
        "POST",
        "/applications/upload-coroners-letter",
    ): Permission.APPLICATION_CREATE,
    (
        "POST",
        "/applications/{laa_reference}/claim",
    ): Permission.CLAIM_CREATE,
    ("POST", "/applications/{laa_reference}/note"): Permission.CASE_NOTE_CREATE,
    ("GET", "/applications/"): Permission.APPLICATION_READ,
    ("GET", "/applications/public-bodies"): [
        Permission.APPLICATION_CREATE,
        Permission.APPLICATION_MANAGE,
    ],
    ("GET", "/applications/search"): Permission.APPLICATION_SEARCH,
    (
        "GET",
        "/applications/provider-offices/{firm_id}",
    ): Permission.PROVIDER_OFFICES_READ,
    ("GET", "/applications/{laa_reference}"): Permission.APPLICATION_READ,
    ("GET", "/applications/{laa_reference}/certificate"): Permission.CERTIFICATE_READ,
    ("GET", "/applications/{laa_reference}/claims"): Permission.CLAIM_READ,
    (
        "GET",
        "/applications/{laa_reference}/claims/{claim_reference}",
    ): Permission.CLAIM_READ,
    (
        "GET",
        "/applications/{laa_reference}/coroners-letter",
    ): Permission.APPLICATION_READ,
    ("GET", "/applications/{laa_reference}/history"): Permission.HISTORY_READ,
    (
        "PATCH",
        "/applications/{laa_reference}/claims/{claim_reference}/pay-in-full",
    ): Permission.CLAIM_MANAGE,
    (
        "PATCH",
        "/applications/{laa_reference}/claims/{claim_reference}/reject",
    ): Permission.CLAIM_MANAGE,
    (
        "PATCH",
        "/applications/{laa_reference}/grant-decision",
    ): Permission.APPLICATION_MANAGE,
    (
        "PATCH",
        "/applications/{laa_reference}/public-bodies",
    ): Permission.APPLICATION_MANAGE,
    (
        "PATCH",
        "/applications/{laa_reference}/refuse-decision",
    ): Permission.APPLICATION_MANAGE,
    (
        "DELETE",
        "/applications/coroners-letter/{coroners_letter_id}",
    ): Permission.APPLICATION_CREATE,
    # Claims
    ("POST", "/claims/evidence"): Permission.CLAIM_CREATE,
    ("GET", "/claims/{claim_evidence_id}"): [
        Permission.CLAIM_CREATE,
        Permission.CLAIM_READ,
    ],
    (
        "DELETE",
        "/claims/{claim_evidence_id}",
    ): Permission.CLAIM_CREATE,
    # Notifications
    ("POST", "/notifications/callback"): PUBLIC,
    # Reports
    (
        "GET",
        "/reports/applications/backlog",
    ): Permission.REPORTS_APPLICATION_WORKFLOW_READ,
    ("GET", "/reports/claims/backlog"): Permission.REPORTS_CLAIM_WORKFLOW_READ,
    ("GET", "/reports/payment-extract"): Permission.REPORTS_PAYMENT_READ,
    # Monitoring
    ("GET", "/health"): PUBLIC,
    ("GET", "/status"): PUBLIC,
}


def _walk_dependencies(dependant: Dependant) -> Iterator[Dependant]:
    for dependency in dependant.dependencies:
        yield dependency
        yield from _walk_dependencies(dependency)


class RouteWithDependencies(Protocol):
    dependant: Dependant


def _configured_permissions(
    route: RouteWithDependencies,
) -> list[Permission] | Permission | None:
    permissions = [
        permission
        for dependency in _walk_dependencies(route.dependant)
        if isinstance(dependency.call, PermissionChecker)
        for permission in dependency.call.possible_permissions
    ]

    if not permissions:
        return PUBLIC
    return permissions if len(permissions) > 1 else permissions[0]


def test_every_route_has_the_expected_permission():
    app = create_app()

    actual = {
        (method, route.path): _configured_permissions(route)
        for route in iter_route_contexts(app.routes)
        if isinstance(getattr(route, "original_route", route), APIRoute)
        for method in route.methods
    }

    assert actual == EXPECTED_ROUTE_PERMISSIONS
    assert list(actual.items()) == list(EXPECTED_ROUTE_PERMISSIONS.items())
