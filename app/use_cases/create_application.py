from app.models.application.index import Application, ApplicationCreate
from app.ports.create_application_port import CreateApplicationPort
from app.ports.gov_notify_port import GovNotifyPort


class CreateApplicationUseCase:
    def __init__(
        self,
        create_application_port: CreateApplicationPort,
        gov_notify_port: GovNotifyPort,
    ) -> None:
        self.create_application_port = create_application_port
        self.gov_notify_port = gov_notify_port

    def execute(self, request: ApplicationCreate, firm_code: str) -> Application:
        application = self.create_application_port.create_application(
            request, firm_code
        )

        try:
            self.gov_notify_port.send_application_submit_confirmation_email(
                application,
                request.provider.email_address,
            )
            self.create_application_port.commit()
        except Exception:
            self.create_application_port.rollback()
            raise

        return application
