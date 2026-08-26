import logging

from app.contexts.user import get_entra_user_name
from app.logging_utils import build_log_extra
from app.models.application.enums import MeritsDecision, PublicBodyId
from app.models.history.enums import ActorType, HistoryEventReference
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.ports.update_application_public_bodies_port import ApplicationPublicBodiesPort
from app.use_cases.exceptions import (
    ApplicationNotFoundError,
    ApplicationNotGrantedError,
)

logger = logging.getLogger(__name__)


class UpdatePublicBodiesUseCase:
    def __init__(
        self,
        application_lookup_port: ApplicationLookupPort,
        update_public_bodies_port: ApplicationPublicBodiesPort,
        create_history_event_port: CreateHistoryEventPort,
    ) -> None:
        self.application_lookup_port = application_lookup_port
        self.update_public_bodies_port = update_public_bodies_port
        self.create_history_event_port = create_history_event_port

    def execute(self, laa_reference: str, public_body_ids: list[PublicBodyId]) -> None:
        application = self.application_lookup_port.get_application_by_laa_reference(
            laa_reference
        )
        if application is None:
            raise ApplicationNotFoundError(f"Application {laa_reference} not found")

        if application.overall_decision != MeritsDecision.GRANTED:
            raise ApplicationNotGrantedError(
                f"Application {laa_reference} is not granted"
            )

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
            old_public_bodies = [
                application_public_body.public_body_id
                for application_public_body in application.public_bodies
            ]
            self.update_public_bodies_port.update_public_bodies(
                application=application,
                public_body_ids=public_body_ids,
            )
            self.create_history_event_port.create_history_event(
                event_reference=HistoryEventReference.INTERESTED_PARTY_UPDATED,
                actor=get_entra_user_name(),
                actor_type=ActorType.CASEWORKER,
                laa_reference=application.laa_reference,
                event_data={
                    "old_public_bodies": old_public_bodies,
                    "new_public_bodies": public_body_ids,
                },
            )
            self.update_public_bodies_port.commit()
        except Exception:
            self.update_public_bodies_port.rollback()
            raise
