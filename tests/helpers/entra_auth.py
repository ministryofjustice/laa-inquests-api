from unittest.mock import MagicMock


from app import api
from app.ports.entra_auth_port import AuthenticatedUser
from app.routers.dependencies import get_entra_auth_port


def override_entra_auth_app_roles(app_roles: set[str]) -> None:
    def get_entra_auth_port_override():
        mock_auth = MagicMock()
        mock_auth.verify_token.return_value = AuthenticatedUser(
            firm_code="0A123B",
            scopes=frozenset({"User.Provider"}),
            app_roles=frozenset(app_roles),
            name="Test Name",
            entra_object_id="some-entra-object-id",
        )
        return mock_auth

    api.dependency_overrides[get_entra_auth_port] = get_entra_auth_port_override
