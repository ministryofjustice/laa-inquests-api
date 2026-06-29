from abc import ABC, abstractmethod
import uuid

from app.models.application.index import CoronersLetter


class UploadCoronersLetterPort(ABC):
    @abstractmethod
    def save_uploaded_coroners_letter(
        self,
        coroners_letter: CoronersLetter,
    ) -> uuid.UUID: ...
