import uuid
from abc import ABC, abstractmethod

from app.domain.coroners_letter import CoronersLetter


class GetCoronersLetterPort(ABC):
    @abstractmethod
    def get_coroners_letter_by_id(
        self,
        coroners_letter_id: uuid.UUID,
    ) -> CoronersLetter | None: ...
