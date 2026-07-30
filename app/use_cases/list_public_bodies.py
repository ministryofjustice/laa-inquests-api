from app.models.application.index import PublicBody
from app.ports.list_public_bodies_port import ListPublicBodiesPort


class ListPublicBodiesUseCase:
    def __init__(self, list_public_bodies_port: ListPublicBodiesPort) -> None:
        self.list_public_bodies_port = list_public_bodies_port

    def execute(self) -> list[PublicBody]:
        return self.list_public_bodies_port.list_public_bodies()
