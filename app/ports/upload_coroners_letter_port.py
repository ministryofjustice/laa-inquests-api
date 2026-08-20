import uuid
from abc import ABC, abstractmethod

from app.domain.coroners_letter import CoronersLetter


class UploadCoronersLetterPort(ABC):
    @abstractmethod
    def save_uploaded_coroners_letter(
        self,
        coroners_letter: CoronersLetter,
    ) -> uuid.UUID: ...
