import logging

from app.contexts.user import get_entra_user_name
from app.logging_utils import build_log_extra
from app.models.history.enums import ActorType, HistoryEventReference
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.use_cases.exceptions import ApplicationNotFoundError

logger = logging.getLogger(__name__)


class CreateNoteUseCase:
    def __init__(
        self,
        application_lookup_port: ApplicationLookupPort,
        create_history_event_port: CreateHistoryEventPort,
    ) -> None:
        self.application_lookup_port = application_lookup_port
        self.create_history_event_port = create_history_event_port

    def execute(self, laa_reference: str, note_text: str) -> None:
        application = self.application_lookup_port.get_application_by_laa_reference(
            laa_reference
        )
        if application is None:
            logger.error(
                "Create note failed: application not found",
                extra=build_log_extra(
                    event="create_note_failed",
                    laa_reference=laa_reference,
                ),
            )
            raise ApplicationNotFoundError(f"Application {laa_reference} not found")

        try:
            self.create_history_event_port.create_history_event(
                event_reference=HistoryEventReference.CASE_NOTE_ADDED,
                actor=get_entra_user_name(),
                actor_type=ActorType.CASEWORKER,
                application_id=application.application_id,
                event_data={"note_text": note_text},
            )
            self.create_history_event_port.commit()
            logger.info(
                "Case note created",
                extra=build_log_extra(
                    event="create_note_completed",
                    laa_reference=application.laa_reference,
                ),
            )
        except Exception:
            logger.exception(
                "Create note failed",
                extra=build_log_extra(
                    event="create_note_failed",
                    laa_reference=application.laa_reference,
                ),
            )
            self.create_history_event_port.rollback()
            raise
