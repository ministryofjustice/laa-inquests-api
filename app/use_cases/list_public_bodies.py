import logging
import re

from app.logging_utils import build_log_extra
from app.models.application.index import PublicBody
from app.ports.list_public_bodies_port import ListPublicBodiesPort

logger = logging.getLogger(__name__)


def _sort_key(body: PublicBody) -> str:
    # Normalise "Department of X" to "Department for X" so both sort identically
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
        public_bodies = sorted(
            self.list_public_bodies_port.list_public_bodies(), key=_sort_key
        )
        logger.info(
            "Public bodies listed",
            extra=build_log_extra(
                event="public_bodies_list_completed",
                result_count=len(public_bodies),
            ),
        )
        return public_bodies
