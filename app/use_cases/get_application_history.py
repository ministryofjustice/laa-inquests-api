from app.ports.get_application_history_port import GetApplicationHistoryPort
from app.ports.get_application_port import GetApplicationPort
from app.use_cases.exceptions import ApplicationNotFoundError


class GetApplicationHistoryUseCase:
    def __init__(
        self,
        get_application_history_port: GetApplicationHistoryPort,
        get_application_port: GetApplicationPort,
    ):
        self.get_application_history_port = get_application_history_port
        self.get_application_port = get_application_port

    def execute(self, laa_reference):
        application = self.get_application_port.get_application_by_laa_reference(
            laa_reference
        )
        if application is None:
            raise ApplicationNotFoundError(
                f"No application found for laa_reference: {laa_reference}"
            )

        return self.get_application_history_port.get_application_history(laa_reference)
