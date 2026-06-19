from typing import Protocol

from app.models.application.index import CoronersLetterResponse


class SdsPort(Protocol):
    def save_coroners_letter(
        self, coroners_letter: bytes, file_name: str
    ) -> CoronersLetterResponse: ...