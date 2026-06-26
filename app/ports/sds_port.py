from abc import ABC, abstractmethod

from app.models.application.index import SDSUploadCoronersLetterResponse


class SdsPort(ABC):
    @abstractmethod
    def save_coroners_letter(
        self, coroners_letter: bytes, file_name: str
    ) -> SDSUploadCoronersLetterResponse: ...
