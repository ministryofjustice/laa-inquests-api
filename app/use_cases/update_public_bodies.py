import logging

from app.logging_utils import build_log_extra
from app.models.application.enums import PublicBodyId
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.update_application_public_bodies_port import ApplicationPublicBodiesPort
from app.use_cases.exceptions import ApplicationNotFoundError

logger = logging.getLogger(__name__)


class UpdatePublicBodiesUseCase:
    def __init__(
        self,
        application_lookup_port: ApplicationLookupPort,
        update_public_bodies_port: ApplicationPublicBodiesPort,
    ) -> None:
        self.application_lookup_port = application_lookup_port
        self.update_public_bodies_port = update_public_bodies_port

    def execute(self, laa_reference: str, public_body_ids: list[PublicBodyId]) -> None:
        application = self.application_lookup_port.get_application_by_laa_reference(
            laa_reference
        )
        if application is None:
            raise ApplicationNotFoundError(f"Application {laa_reference} not found")

        if not public_body_ids:
            logger.warning(
                "No public bodies provided for updating",
                extra=build_log_extra(
                    event="application_repository_update_public_bodies_failed",
                    laa_reference=laa_reference,
                ),
            )
            raise ValueError("At least one public body must be provided.")

        try:
            self.update_public_bodies_port.update_public_bodies(
                application=application,
                public_body_ids=public_body_ids,
            )
            self.update_public_bodies_port.commit()
        except Exception:
            self.update_public_bodies_port.rollback()
            raise
