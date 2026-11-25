"""Shared auth helpers for E2E tests."""

from dataclasses import replace

from app import api
from app.routers.dependencies import get_entra_auth_port


def set_token_office_codes(office_codes: set[str]) -> None:
    """Make the mocked Entra token carry these office codes instead of the default."""
    auth = api.dependency_overrides[get_entra_auth_port]()
    verify_token = auth.verify_token.side_effect

    def verify_with_offices(role, required_scopes=None):
        user = verify_token(role, required_scopes)
        return replace(user, office_codes=frozenset(office_codes))

    auth.verify_token.side_effect = verify_with_offices
    api.dependency_overrides[get_entra_auth_port] = lambda: auth
