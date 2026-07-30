import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient

ENTRA_JWKS_URL = "https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"


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

    def verify_token(self, token: str, required_scopes: set[str] | None = None) -> None:
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
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
