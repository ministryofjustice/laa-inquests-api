from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AuthenticatedUser:
    firm_code: str | None
    scopes: frozenset[str]
    name: str


class EntraAuthPort(Protocol):
    def verify_token(
        self, token: str, required_scopes: set[str] | None = None
    ) -> AuthenticatedUser: ...
