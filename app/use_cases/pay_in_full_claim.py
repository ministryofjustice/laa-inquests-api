import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.contexts.user import get_entra_user_name
from app.domain.claim_error import ClaimValidationError
from app.domain.pay_in_full import PayInFullClaim
from app.domain.payment_extract import (
    PaymentExtractLine,
    RecoupmentSourceLine,
    build_final_bill_disbursement_extract,
    build_final_bill_fees_extract,
    build_recoupment_extract,
)
from app.models.claim.enums import ClaimDecisionStatus, ClaimStatus, ClaimType
from app.models.claim.index import Claim
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.notifications.enums import NotificationType
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.create_claim_decision_amount_port import (
    CreateClaimDecisionAmountPort,
)
from app.ports.claim.create_claim_decision_port import CreateClaimDecisionPort
from app.ports.claim.create_payment_extract_port import CreatePaymentExtractPort
from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.ports.claim.get_claims_for_application_port import GetClaimsForApplicationPort
from app.ports.claim.get_payment_extracts_for_claim_port import (
    GetPaymentExtractsForClaimPort,
)
from app.ports.claim.update_claim_status_port import UpdateClaimStatusPort
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.ports.gov_notify_port import GovNotifyPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import (
    ApplicationNotFoundError,
    ClaimNotFoundError,
    InvalidClaimError,
)

logger = logging.getLogger(__name__)


def _to_json_amount(amount: Decimal | None) -> str | None:
    return str(amount) if amount is not None else None


@dataclass(frozen=True)
class PayInFullClaimCommand:
    laa_reference: str
    claim_reference: str
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
        provider_details_port: ProviderDetailsPort | None = None,
        gov_notify_port: GovNotifyPort | None = None,
        get_claims_for_application_port: GetClaimsForApplicationPort | None = None,
        get_payment_extracts_for_claim_port: GetPaymentExtractsForClaimPort
        | None = None,
        create_payment_extract_port: CreatePaymentExtractPort | None = None,
    ) -> None:
        self.application_lookup_port = application_lookup_port
        self.get_claim_by_id_port = get_claim_by_id_port
        self.create_claim_decision_port = create_claim_decision_port
        self.create_claim_decision_amount_port = create_claim_decision_amount_port
        self.update_claim_status_port = update_claim_status_port
        self.create_history_event_port = create_history_event_port
        self.provider_details_port = provider_details_port
        self.gov_notify_port = gov_notify_port
        self.get_claims_for_application_port = get_claims_for_application_port
        self.get_payment_extracts_for_claim_port = get_payment_extracts_for_claim_port
        self.create_payment_extract_port = create_payment_extract_port

    def execute(self, command: PayInFullClaimCommand) -> None:
        application = self.application_lookup_port.get_application_by_laa_reference(
            command.laa_reference
        )
        if application is None:
            raise ApplicationNotFoundError(command.laa_reference)

        claim = self.get_claim_by_id_port.get_claim_by_reference(
            command.claim_reference
        )
        if claim is None or claim.application_id != application.application_id:
            raise ClaimNotFoundError(command.claim_reference)

        try:
            decision_amounts = PayInFullClaim(
                profit_cost_net=command.profit_cost_net,
                profit_cost_gross=command.profit_cost_gross,
                profit_cost_vat_zero=command.profit_cost_vat_zero,
                disbursement_net=command.disbursement_net,
                disbursement_gross=command.disbursement_gross,
                disbursement_vat_zero=command.disbursement_vat_zero,
            )
            decision_amounts.validate()
        except ClaimValidationError as e:
            raise InvalidClaimError(code=e.code, message=e.message) from e

        try:
            claim_decision = self.create_claim_decision_port.create_claim_decision(
                claim_id=claim.claim_id,
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
                claim_id=claim.claim_id,
                status=ClaimStatus.PAY_IN_FULL,
            )

            self._create_payment_extract(
                claim=claim,
                application_id=application.application_id,
                command=command,
                decision_date=claim_decision.created_at.date(),
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

            firm_name = self.provider_details_port.get_firm_name(
                application.provider.firm_code
            )
            self.gov_notify_port.send_claim_final_bill_paid_decision_email(
                claim=claim,
                application=application,
                recipient_email=application.provider.email_address,
                firm_name=firm_name,
                decision_amounts=decision_amounts,
            )
            self.create_history_event_port.create_history_event(
                event_reference=HistoryEventReference.CLAIM_FINAL_BILL_PAID_EMAIL,
                actor=ActorType.SYSTEM,
                actor_type=ActorType.SYSTEM,
                application_id=application.application_id,
                event_data={
                    "recipient": application.provider.email_address,
                    "channel": NotificationType.EMAIL,
                },
            )

            self.update_claim_status_port.commit()
        except Exception:
            self.update_claim_status_port.rollback()
            raise

    def _create_payment_extract(
        self,
        claim: Claim,
        application_id: int,
        command: PayInFullClaimCommand,
        decision_date: date,
    ) -> None:
        if self.create_payment_extract_port is None:
            return

        lines: list[PaymentExtractLine] = []
        sequence = 1
        invoice_date = claim.submission_date.date()

        fees_line = build_final_bill_fees_extract(
            claim_id=claim.claim_id,
            sequence=sequence,
            invoice_date=invoice_date,
            gross=command.profit_cost_gross,
            vat_zero_amount=command.profit_cost_vat_zero,
        )
        if fees_line is not None:
            lines.append(fees_line)
            sequence += 1

        disbursement_lines = build_final_bill_disbursement_extract(
            claim_id=claim.claim_id,
            start_sequence=sequence,
            invoice_date=invoice_date,
            gross=command.disbursement_gross,
            vat_zero_amount=command.disbursement_vat_zero,
        )
        lines.extend(disbursement_lines)
        sequence += len(disbursement_lines)

        for poa_claim in self._recoupable_poa_claims(application_id, claim.claim_id):
            sources = [
                RecoupmentSourceLine(
                    invoice_number=extract.invoice_number,
                    invoice_amount=extract.invoice_amount,
                    tax_code=extract.tax_code,
                )
                for extract in self.get_payment_extracts_for_claim_port.get_payment_extracts_by_claim_id(
                    poa_claim.claim_id
                )
            ]
            recoupment_lines = build_recoupment_extract(
                start_sequence=sequence,
                invoice_date=decision_date,
                original_lines=sources,
            )
            lines.extend(recoupment_lines)
            sequence += len(recoupment_lines)

        if lines:
            self.create_payment_extract_port.create_payment_extract(
                claim_id=claim.claim_id,
                lines=lines,
            )

    def _recoupable_poa_claims(
        self, application_id: int, current_claim_id: int
    ) -> list[Claim]:
        if self.get_claims_for_application_port is None:
            return []

        claims = self.get_claims_for_application_port.get_claims_by_application_id(
            application_id
        )
        return [
            claim
            for claim in claims
            if claim.claim_id != current_claim_id
            and claim.claim_type_id == ClaimType.PAYMENT_ON_ACCOUNT
            and claim.status_id == ClaimStatus.PAY_IN_FULL
        ]
