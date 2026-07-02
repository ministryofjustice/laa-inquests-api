from typing import Protocol


class EntraAuthPort(Protocol):
    def verify_token(
        self, token: str, required_scopes: set[str] | None = None
    ) -> None: ...
