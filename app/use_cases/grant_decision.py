from app.models.application.enums import MeritsDecision
from app.ports.update_decision_port import ApplicationDecisionPort
from app.use_cases.exceptions import ApplicationNotFoundError, ProceedingsNotFoundError


class GrantDecisionUseCase:
    def __init__(
        self,
        application_decision_port: ApplicationDecisionPort,
    ) -> None:
        self.application_decision_port = application_decision_port

    def execute(self, laa_reference: str) -> None:
        application = self.application_decision_port.get_application_by_laa_reference(
            laa_reference
        )
        if application is None:
            raise ApplicationNotFoundError(f"Application {laa_reference} not found")

        if not application.proceedings:
            raise ProceedingsNotFoundError(
                f"No proceedings found for application {laa_reference}"
            )

        proceeding = application.proceedings[0]
        proceeding.merits_decision = MeritsDecision.GRANTED
        proceeding.reason_for_refusal = None
        proceeding.justification = None

        self.application_decision_port.update_decision(proceeding)
        self.application_decision_port.commit()
