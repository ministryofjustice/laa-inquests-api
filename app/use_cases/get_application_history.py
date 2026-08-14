import logging

from app.logging_utils import build_log_extra
from app.models.history.enums import ActorType
from app.models.history.index import HistoryEvent, HistoryEventResponse
from app.ports.get_application_history_port import GetApplicationHistoryPort
from app.ports.get_application_port import GetApplicationPort
from app.use_cases.exceptions import ApplicationNotFoundError

logger = logging.getLogger(__name__)


class GetApplicationHistoryUseCase:
    def __init__(
        self,
        get_application_history_port: GetApplicationHistoryPort,
        get_application_port: GetApplicationPort,
    ):
        self.get_application_history_port = get_application_history_port
        self.get_application_port = get_application_port

    def execute(self, laa_reference: int) -> list[HistoryEventResponse]:
        application = self.get_application_port.get_application_by_laa_reference(
            laa_reference
        )
        if application is None:
            raise ApplicationNotFoundError(
                f"No application found for laa_reference: {laa_reference}"
            )

        history_events = self.get_application_history_port.get_application_history(
            laa_reference
        )
        response = [self._create_history_response(event) for event in history_events]
        logger.info(
            "Application history retrieved",
            extra=build_log_extra(
                event="application_history_list_completed",
                laa_reference=laa_reference,
                result_count=len(response),
            ),
        )
        return response

    def _create_history_response(self, event: HistoryEvent) -> HistoryEventResponse:
        response = HistoryEventResponse.model_validate(event)
        if event.actor_type == ActorType.PROVIDER:
            response.actor = "Provider"
        return response
