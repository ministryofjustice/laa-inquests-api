from abc import ABC, abstractmethod

from app.models.application.enums import PublicBodyId
from app.models.application.index import Application


class ApplicationPublicBodiesPort(ABC):
    @abstractmethod
    def update_public_bodies(
        self,
        application: Application,
        public_body_ids: list[PublicBodyId],
    ) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
