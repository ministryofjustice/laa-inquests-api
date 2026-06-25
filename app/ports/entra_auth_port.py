from typing import Protocol


class EntraAuthPort(Protocol):
    def verify_token(self, token: str) -> None: ...
