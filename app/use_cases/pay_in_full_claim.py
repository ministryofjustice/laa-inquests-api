from dataclasses import dataclass
from decimal import Decimal

from app.contexts.user import get_entra_user_name
from app.domain.claim_error import ClaimValidationError
from app.domain.pay_in_full import PayInFullClaim
from app.domain.payment_extract import (
    build_final_bill_fee_lines,
    build_recoupment_line,
)
from app.models.claim.enums import ClaimDecisionStatus, ClaimStatus, ClaimType
from app.models.claim.index import Claim, ClaimDecision
from app.models.history.enums import ActorType, HistoryEventReference
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.create_claim_decision_amount_port import (
    CreateClaimDecisionAmountPort,
)
from app.ports.claim.create_claim_decision_port import CreateClaimDecisionPort
from app.ports.claim.create_payment_extract_port import CreatePaymentExtractPort
from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.ports.claim.get_claim_payment_extracts_port import (
    GetClaimPaymentExtractsPort,
)
from app.ports.claim.list_recoupable_poa_extracts_port import (
    ListRecoupablePoaExtractsPort,
)
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
        create_payment_extract_port: CreatePaymentExtractPort | None = None,
        get_claim_payment_extracts_port: GetClaimPaymentExtractsPort | None = None,
        list_recoupable_poa_extracts_port: ListRecoupablePoaExtractsPort | None = None,
    ) -> None:
        self.application_lookup_port = application_lookup_port
        self.get_claim_by_id_port = get_claim_by_id_port
        self.create_claim_decision_port = create_claim_decision_port
        self.create_claim_decision_amount_port = create_claim_decision_amount_port
        self.update_claim_status_port = update_claim_status_port
        self.create_history_event_port = create_history_event_port
        self.create_payment_extract_port = create_payment_extract_port
        self.get_claim_payment_extracts_port = get_claim_payment_extracts_port
        self.list_recoupable_poa_extracts_port = list_recoupable_poa_extracts_port

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

            self._create_final_bill_payment_extract(application, claim, claim_decision)

            self.update_claim_status_port.commit()
        except Exception:
            self.update_claim_status_port.rollback()
            raise

    def _create_final_bill_payment_extract(
        self,
        application,
        claim: Claim,
        claim_decision: ClaimDecision,
    ) -> None:
        if (
            claim.claim_type_id != ClaimType.FINAL_BILL
            or self.create_payment_extract_port is None
            or self.get_claim_payment_extracts_port is None
            or self.list_recoupable_poa_extracts_port is None
        ):
            return

        existing = self.get_claim_payment_extracts_port.get_payment_extracts_for_claim(
            claim.claim_id
        )
        if existing:
            return

        fee_lines = build_final_bill_fee_lines(
            claim_id=claim.claim_id,
            submission_date=claim.submission_date,
            gross=claim.total_profit_cost_gross,
            vat_zero=claim.total_profit_cost_vat_zero,
        )
        for line in fee_lines:
            self.create_payment_extract_port.create_payment_extract(
                claim_id=claim.claim_id,
                line=line,
            )

        sequence = fee_lines[-1].sequence_number + 1
        decision_date = claim_decision.created_at.date()
        recoupable = (
            self.list_recoupable_poa_extracts_port.list_recoupable_poa_extracts(
                application.application_id
            )
        )
        for extract in recoupable:
            self.create_payment_extract_port.create_payment_extract(
                claim_id=claim.claim_id,
                line=build_recoupment_line(
                    claim_id=claim.claim_id,
                    sequence=sequence,
                    original_amount=extract.invoice_amount,
                    tax_code=extract.tax_code,
                    decision_date=decision_date,
                ),
            )
            sequence += 1
