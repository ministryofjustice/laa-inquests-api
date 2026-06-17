from typing import Protocol


class SdsPort(Protocol):
    def save_coroners_letter(self, coroners_letter: str) -> str | None: ...
