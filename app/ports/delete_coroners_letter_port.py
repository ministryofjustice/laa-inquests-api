import uuid
from abc import ABC, abstractmethod


class DeleteCoronersLetterPort(ABC):
    @abstractmethod
    def delete_coroners_letter_by_id(
        self,
        coroners_letter_id: uuid.UUID,
    ) -> bool: ...
