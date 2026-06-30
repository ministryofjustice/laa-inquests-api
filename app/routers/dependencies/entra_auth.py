from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.adapters.entra_auth_adapter import EntraAuthAdapter
from app.config import Config
from app.ports.entra_auth_port import EntraAuthPort

_http_bearer = HTTPBearer(auto_error=False)


def _configured_entra_scopes() -> set[str]:
    return {
        scope.strip()
        for scope in Config.ENTRA_ALLOWED_SCOPES.split(",")
        if scope.strip()
    }


def get_entra_auth_port() -> EntraAuthPort:
    return EntraAuthAdapter(
        tenant_id=Config.ENTRA_TENANT_ID,
        client_id=Config.ENTRA_API_CLIENT_ID,
        default_scopes=_configured_entra_scopes(),
    )


def verify_entra_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
    entra_auth: Annotated[EntraAuthPort, Depends(get_entra_auth_port)],
) -> None:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    entra_auth.verify_token(credentials.credentials)


def verify_entra_provider_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
    entra_auth: Annotated[EntraAuthPort, Depends(get_entra_auth_port)],
) -> None:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    entra_auth.verify_token(credentials.credentials, {"User.Provider"})


def verify_entra_caseworker_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
    entra_auth: Annotated[EntraAuthPort, Depends(get_entra_auth_port)],
) -> None:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    entra_auth.verify_token(credentials.credentials, {"User.Caseworker"})
