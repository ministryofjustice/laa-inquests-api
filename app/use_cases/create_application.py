from app.models.application.index import Application, ApplicationCreate
from app.models.history.enums import ActorType, HistoryEventReference
from app.ports.create_application_port import CreateApplicationPort
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.ports.gov_notify_port import GovNotifyPort


class CreateApplicationUseCase:
    def __init__(
        self,
        create_application_port: CreateApplicationPort,
        create_history_event_port: CreateHistoryEventPort,
        gov_notify_port: GovNotifyPort,
    ) -> None:
        self.create_application_port = create_application_port
        self.create_history_event_port = create_history_event_port
        self.gov_notify_port = gov_notify_port

    def execute(self, request: ApplicationCreate, firm_code: str) -> Application:
        application = self.create_application_port.create_application(
            request, firm_code
        )

        try:
            self.create_history_event_port.create_history_event(
                event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
                actor=request.provider.email_address,
                actor_type=ActorType.PROVIDER,
                event_description="Application received",
                laa_reference=application.laa_reference,
                event_data=None,
            )
            self.gov_notify_port.send_application_submit_confirmation_email(
                application,
                request.provider.email_address,
            )
            self.create_application_port.commit()
            self.create_history_event_port.commit()
        except Exception:
            self.create_application_port.rollback()
            self.create_history_event_port.rollback()
            raise

        return application
