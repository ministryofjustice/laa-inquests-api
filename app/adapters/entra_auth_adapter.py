import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, status

ENTRA_JWKS_URL = "https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"


class EntraAuthAdapter:
    def __init__(self, tenant_id: str, client_id: str) -> None:
        self.client_id = client_id
        self._jwks_client = PyJWKClient(ENTRA_JWKS_URL.format(tenant_id=tenant_id))

    def verify_token(self, token: str) -> None:
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
