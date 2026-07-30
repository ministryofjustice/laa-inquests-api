import re

from app.models.application.index import PublicBody
from app.ports.list_public_bodies_port import ListPublicBodiesPort


def _sort_key(body: PublicBody) -> str:
    # Normalise "Department of X" to "Department for X" so both sort identically;
    return re.sub(
        r"^Department of ",
        "Department for ",
        body.public_body_description,
        flags=re.IGNORECASE,
    )


class ListPublicBodiesUseCase:
    def __init__(self, list_public_bodies_port: ListPublicBodiesPort) -> None:
        self.list_public_bodies_port = list_public_bodies_port

    def execute(self) -> list[PublicBody]:
        return sorted(self.list_public_bodies_port.list_public_bodies(), key=_sort_key)
