from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.adapters.entra_auth_adapter import EntraAuthAdapter
from app.config import Config
from app.contexts.user import set_entra_user_context
from app.ports.entra_auth_port import AuthenticatedUser, EntraAuthPort

_http_bearer = HTTPBearer(auto_error=False)


def _configured_entra_scopes() -> set[str]:
    return {
        scope.strip()
        for scope in Config.ENTRA_ALLOWED_SCOPES.split(",")
        if scope.strip()
    }


def get_entra_auth_port() -> EntraAuthPort:
    return EntraAuthAdapter(
        tenant_id=Config.INQUESTS_API_TENANT_ID,
        client_id=Config.INQUESTS_API_CLIENT_ID,
        default_scopes=_configured_entra_scopes(),
    )


async def verify_entra_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
    entra_auth: Annotated[EntraAuthPort, Depends(get_entra_auth_port)],
) -> AuthenticatedUser:
    return await _verify_entra_token_with_scopes(
        credentials, entra_auth, _configured_entra_scopes()
    )


async def verify_entra_provider_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
    entra_auth: Annotated[EntraAuthPort, Depends(get_entra_auth_port)],
) -> AuthenticatedUser:
    return await _verify_entra_token_with_scopes(
        credentials, entra_auth, {"User.Provider"}
    )


def get_current_provider_firm_code(
    user: Annotated[AuthenticatedUser, Depends(verify_entra_provider_token)],
) -> str:
    if not user.firm_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Provider firm code missing from token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user.firm_code


async def verify_entra_caseworker_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
    entra_auth: Annotated[EntraAuthPort, Depends(get_entra_auth_port)],
) -> AuthenticatedUser:
    return await _verify_entra_token_with_scopes(
        credentials, entra_auth, {"User.Caseworker"}
    )


async def verify_entra_provider_or_caseworker_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
    entra_auth: Annotated[EntraAuthPort, Depends(get_entra_auth_port)],
) -> AuthenticatedUser:
    return await _verify_entra_token_with_scopes(
        credentials, entra_auth, {"User.Provider", "User.Caseworker"}
    )


async def _verify_entra_token_with_scopes(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
    entra_auth: Annotated[EntraAuthPort, Depends(get_entra_auth_port)],
    required_scopes: set[str],
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await run_in_threadpool(
        entra_auth.verify_token, credentials.credentials, required_scopes
    )
    set_entra_user_context(user.entra_object_id, user.name)
    return user
