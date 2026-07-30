from abc import ABC, abstractmethod

from app.models.application.index import PublicBody


class ListPublicBodiesPort(ABC):
    @abstractmethod
    def list_public_bodies(self) -> list[PublicBody]: ...
