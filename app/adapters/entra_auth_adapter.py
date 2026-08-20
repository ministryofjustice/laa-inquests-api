import logging
import re

import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient

from app.logging_utils import build_log_extra
from app.ports.entra_auth_port import AuthenticatedUser

ENTRA_JWKS_URL = "https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"

logger = logging.getLogger(__name__)


class EntraAuthAdapter:
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        default_scopes: set[str] | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.default_scopes = default_scopes or set()
        self._jwks_client = PyJWKClient(ENTRA_JWKS_URL.format(tenant_id=tenant_id))

    def _validate_scopes_or_roles(
        self, payload: dict, required_scopes: set[str] | None
    ) -> None:
        if not required_scopes:
            return

        token_scopes = set((payload.get("scp") or "").split())
        token_roles = set(payload.get("roles") or [])

        if required_scopes.isdisjoint(token_scopes | token_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def _format_name(self, name: str | None) -> str | None:
        if name is None:
            return ""
        cleaned = re.sub(r"\[.*?\]", "", name)
        cleaned = re.sub(r"\s*-\s*(?=\s|$)", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned or ""

    def verify_token(
        self, token: str, required_scopes: set[str] | None = None
    ) -> AuthenticatedUser:
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=[
                    f"https://login.microsoftonline.com/{self.tenant_id}/v2.0",
                    f"https://sts.windows.net/{self.tenant_id}/",
                ],
            )
            self._validate_scopes_or_roles(
                payload, required_scopes or self.default_scopes
            )
            token_scopes = frozenset((payload.get("scp") or "").split())
            token_roles = frozenset(payload.get("roles") or [])
            logger.debug(
                "Entra token validated",
                extra=build_log_extra(
                    event="entra_token_validated_success",
                ),
            )
            return AuthenticatedUser(
                firm_code=payload.get("FIRM_CODE"),
                scopes=token_scopes | token_roles,
                name=self._format_name(payload.get("name")),
                entra_object_id=payload.get("oid"),
            )
        except HTTPException:
            logger.warning(
                "Entra token validation failed",
                extra=build_log_extra(
                    event="entra_token_validation_failed",
                ),
            )
            raise
        except (jwt.PyJWTError, jwt.PyJWKClientError):
            logger.warning(
                "Entra token validation failed",
                extra=build_log_extra(
                    event="entra_token_validation_failed",
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
