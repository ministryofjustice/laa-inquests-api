from unittest.mock import MagicMock

from fastapi import HTTPException, status

from app import api
from app.ports.entra_auth_port import AuthenticatedUser
from app.routers.dependencies import get_entra_auth_port


def override_entra_auth_port_with_provider_no_role_token() -> None:
    def get_entra_auth_port_override():
        mock_auth = MagicMock()
        tokens = {
            "valid-caseworker-entra-token": {
                "scopes": {"User.Caseworker"},
                "app_roles": set(),
            },
            "valid-provider-application-user-token": {
                "scopes": {"User.Provider"},
                "app_roles": {"Inquests - Provider Application User"},
            },
            "valid-provider-claims-user-token": {
                "scopes": {"User.Provider"},
                "app_roles": {"Inquests - Provider Claims User"},
            },
            "valid-provider-no-role-token": {
                "scopes": {"User.Provider"},
                "app_roles": set(),
            },
        }

        def verify_token(
            token: str, required_scopes: set[str] | None = None
        ) -> AuthenticatedUser:
            if token == "invalid-token" or token not in tokens:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            token_scopes = tokens[token]["scopes"]
            if required_scopes and required_scopes.isdisjoint(token_scopes):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return AuthenticatedUser(
                firm_code="0A123B",
                scopes=frozenset(token_scopes),
                name="Test Name",
                app_roles=frozenset(tokens[token]["app_roles"]),
            )

        mock_auth.verify_token.side_effect = verify_token
        return mock_auth

    api.dependency_overrides[get_entra_auth_port] = get_entra_auth_port_override
