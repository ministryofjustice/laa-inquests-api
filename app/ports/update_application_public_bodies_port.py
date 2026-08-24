from abc import ABC, abstractmethod

from app.models.application.enums import PublicBodyId


class ApplicationPublicBodiesPort(ABC):
    @abstractmethod
    def update_public_bodies(
        self,
        laa_reference: str,
        public_body_ids: list[PublicBodyId],
    ) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
