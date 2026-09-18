from collections.abc import Iterator

from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

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
    ): Permission.CORONERS_LETTER_UPLOAD,
    (
        "POST",
        "/applications/{laa_reference}/claim",
    ): Permission.CLAIM_CREATE,
    ("POST", "/applications/{laa_reference}/note"): Permission.CASE_NOTE_CREATE,
    ("GET", "/applications/"): Permission.APPLICATION_READ,
    ("GET", "/applications/public-bodies"): Permission.PUBLIC_BODIES_READ,
    ("GET", "/applications/search"): Permission.APPLICATION_SEARCH,
    (
        "GET",
        "/applications/provider-offices/{firm_id}",
    ): Permission.PROVIDER_OFFICES_READ,
    ("GET", "/applications/{laa_reference}"): None,
    ("GET", "/applications/{laa_reference}/certificate"): None,
    ("GET", "/applications/{laa_reference}/claims"): None,
    ("GET", "/applications/{laa_reference}/claims/{claim_id}"): None,
    ("GET", "/applications/{laa_reference}/coroners-letter"): None,
    ("GET", "/applications/{laa_reference}/history"): None,
    ("PATCH", "/applications/{laa_reference}/claims/{claim_id}/pay-in-full"): None,
    ("PATCH", "/applications/{laa_reference}/claims/{claim_id}/reject"): None,
    ("PATCH", "/applications/{laa_reference}/grant-decision"): None,
    ("PATCH", "/applications/{laa_reference}/public-bodies"): None,
    ("PATCH", "/applications/{laa_reference}/refuse-decision"): None,
    (
        "DELETE",
        "/applications/coroners-letter/{coroners_letter_id}",
    ): Permission.CORONERS_LETTER_DELETE,
    # Claims
    ("POST", "/claims/evidence"): Permission.CLAIM_EVIDENCE_UPLOAD,
    ("GET", "/claims/{claim_evidence_id}"): None,
    (
        "DELETE",
        "/claims/{claim_evidence_id}",
    ): Permission.CLAIM_DELETE,
    # Notifications
    ("POST", "/notifications/callback"): PUBLIC,
    # Reports
    ("GET", "/reports/applications/backlog"): None,
    ("GET", "/reports/claims/backlog"): None,
    # Monitoring
    ("GET", "/health"): PUBLIC,
    ("GET", "/status"): PUBLIC,
}


def _walk_dependencies(dependant: Dependant) -> Iterator[Dependant]:
    for dependency in dependant.dependencies:
        yield dependency
        yield from _walk_dependencies(dependency)


def _configured_permission(route: APIRoute) -> Permission | None:
    permissions = [
        dependency.call.required_permission
        for dependency in _walk_dependencies(route.dependant)
        if isinstance(dependency.call, PermissionChecker)
    ]

    assert len(permissions) <= 1, (
        f"{route.path} has multiple permission dependencies: {permissions}"
    )

    return permissions[0] if permissions else PUBLIC


def test_every_route_has_the_expected_permission():
    app = create_app()

    actual = {
        (method, route.path): _configured_permission(route)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }

    assert actual == EXPECTED_ROUTE_PERMISSIONS
    assert list(actual.items()) == list(EXPECTED_ROUTE_PERMISSIONS.items())
