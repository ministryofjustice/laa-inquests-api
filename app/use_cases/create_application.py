import logging

from app.logging_utils import build_log_extra
from app.models.application.index import Application, ApplicationCreate
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.notifications.enums import NotificationType
from app.ports.create_application_port import CreateApplicationPort
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.ports.gov_notify_port import GovNotifyPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import ProviderDetailsRetrievalError

logger = logging.getLogger(__name__)


class CreateApplicationUseCase:
    def __init__(
        self,
        create_application_port: CreateApplicationPort,
        create_history_event_port: CreateHistoryEventPort,
        gov_notify_port: GovNotifyPort,
        provider_details_port: ProviderDetailsPort,
    ) -> None:
        self.create_application_port = create_application_port
        self.create_history_event_port = create_history_event_port
        self.gov_notify_port = gov_notify_port
        self.provider_details_port = provider_details_port

    def execute(self, request: ApplicationCreate, firm_code: str) -> Application:
        application = self.create_application_port.create_application(
            request, firm_code
        )

        try:
            if not self.provider_details_port.does_office_exist(
                application.provider.office_id
            ):
                raise ProviderDetailsRetrievalError(
                    f"Office id {application.provider.office_id} does not exist in provider details API"
                )

            self.create_history_event_port.create_history_event(
                event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
                actor=request.provider.email_address,
                actor_type=ActorType.PROVIDER,
                laa_reference=application.laa_reference,
                event_data=None,
            )
            self.gov_notify_port.send_application_submit_confirmation_email(
                application,
                request.provider.email_address,
            )
            self.create_history_event_port.create_history_event(
                event_reference=HistoryEventReference.APPLICATION_SUBMISSION_CONFIRMATION,
                actor="System",
                actor_type=ActorType.SYSTEM,
                laa_reference=application.laa_reference,
                event_data={
                    "recipient": request.provider.email_address,
                    "channel": NotificationType.EMAIL,
                },
            )
            # This commits both the application and the history event in a single transaction
            # because they share a session
            self.create_application_port.commit()
            logger.info(
                "Application submitted",
                extra=build_log_extra(
                    event="application_submitted",
                    laa_reference=application.laa_reference,
                    firm_code=firm_code,
                ),
            )
        except Exception:
            # This rolls back both the application and the history event in case of any failure
            self.create_application_port.rollback()
            logger.warning(
                "Application creation failed and rolled back",
                extra=build_log_extra(
                    event="application_created_failed",
                    firm_code=firm_code,
                ),
                exc_info=True,
            )
            raise

        return application
