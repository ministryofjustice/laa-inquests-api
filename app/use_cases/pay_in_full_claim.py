from dataclasses import dataclass
from decimal import Decimal

from app.contexts.user import get_entra_user_name
from app.domain.claim_error import ClaimValidationError
from app.domain.pay_in_full import PayInFullClaim
from app.models.claim.enums import ClaimDecisionStatus, ClaimStatus
from app.models.history.enums import ActorType, HistoryEventReference
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.create_claim_decision_amount_port import (
    CreateClaimDecisionAmountPort,
)
from app.ports.claim.create_claim_decision_port import CreateClaimDecisionPort
from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.ports.claim.update_claim_status_port import UpdateClaimStatusPort
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.use_cases.exceptions import (
    ApplicationNotFoundError,
    ClaimNotFoundError,
    InvalidClaimError,
)


def _to_json_amount(amount: Decimal | None) -> str | None:
    return str(amount) if amount is not None else None


@dataclass(frozen=True)
class PayInFullClaimCommand:
    laa_reference: str
    claim_id: int
    profit_cost_net: Decimal | None = None
    profit_cost_gross: Decimal | None = None
    profit_cost_vat_zero: Decimal | None = None
    disbursement_net: Decimal | None = None
    disbursement_gross: Decimal | None = None
    disbursement_vat_zero: Decimal | None = None


class PayInFullClaimUseCase:
    def __init__(
        self,
        application_lookup_port: ApplicationLookupPort,
        get_claim_by_id_port: GetClaimByIdPort,
        create_claim_decision_port: CreateClaimDecisionPort,
        create_claim_decision_amount_port: CreateClaimDecisionAmountPort,
        update_claim_status_port: UpdateClaimStatusPort,
        create_history_event_port: CreateHistoryEventPort,
    ) -> None:
        self.application_lookup_port = application_lookup_port
        self.get_claim_by_id_port = get_claim_by_id_port
        self.create_claim_decision_port = create_claim_decision_port
        self.create_claim_decision_amount_port = create_claim_decision_amount_port
        self.update_claim_status_port = update_claim_status_port
        self.create_history_event_port = create_history_event_port

    def execute(self, command: PayInFullClaimCommand) -> None:
        application = self.application_lookup_port.get_application_by_laa_reference(
            command.laa_reference
        )
        if application is None:
            raise ApplicationNotFoundError(command.laa_reference)

        claim = self.get_claim_by_id_port.get_claim_by_id(command.claim_id)
        if claim is None or claim.application_id != application.application_id:
            raise ClaimNotFoundError(command.claim_id)

        try:
            PayInFullClaim(
                profit_cost_net=command.profit_cost_net,
                profit_cost_gross=command.profit_cost_gross,
                profit_cost_vat_zero=command.profit_cost_vat_zero,
                disbursement_net=command.disbursement_net,
                disbursement_gross=command.disbursement_gross,
                disbursement_vat_zero=command.disbursement_vat_zero,
            ).validate()
        except ClaimValidationError as e:
            raise InvalidClaimError(code=e.code, message=e.message) from e

        try:
            claim_decision = self.create_claim_decision_port.create_claim_decision(
                claim_id=command.claim_id,
                decision_status=ClaimDecisionStatus.PAY_IN_FULL,
            )
            self.create_claim_decision_amount_port.create_claim_decision_amount(
                claim_decision_id=claim_decision.claim_decision_id,
                profit_cost_net=command.profit_cost_net,
                profit_cost_gross=command.profit_cost_gross,
                profit_cost_vat_zero=command.profit_cost_vat_zero,
                disbursement_net=command.disbursement_net,
                disbursement_gross=command.disbursement_gross,
                disbursement_vat_zero=command.disbursement_vat_zero,
            )
            self.update_claim_status_port.update_claim_status(
                claim_id=command.claim_id,
                status=ClaimStatus.PAY_IN_FULL,
            )

            self.create_history_event_port.create_history_event(
                event_reference=HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
                actor=get_entra_user_name(),
                actor_type=ActorType.CASEWORKER,
                application_id=application.application_id,
                event_data={
                    "claim_type": claim.claim_type_id,
                    "claim_decision": ClaimStatus.PAY_IN_FULL,
                    "profit_cost_net": _to_json_amount(command.profit_cost_net),
                    "profit_cost_gross": _to_json_amount(command.profit_cost_gross),
                    "profit_cost_vat_zero": _to_json_amount(
                        command.profit_cost_vat_zero
                    ),
                    "disbursement_net": _to_json_amount(command.disbursement_net),
                    "disbursement_gross": _to_json_amount(command.disbursement_gross),
                    "disbursement_vat_zero": _to_json_amount(
                        command.disbursement_vat_zero
                    ),
                },
            )

            self.update_claim_status_port.commit()
        except Exception:
            self.update_claim_status_port.rollback()
            raise
