import os
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import random
import string
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlmodel import Session, exists, select

from app.config import Config
from app.db import CustomSessionLocal
from app.domain.claim import ApprovedClaimAmount, calculate_available_funds
from app.domain.pay_in_full import (
    PayInFullClaim,
    pay_in_full_claim_from_submitted_poa_claim,
)
from app.domain.payment_extract import (
    PaymentExtractLine,
    RecoupmentSourceLine,
    build_final_bill_disbursement_extract,
    build_final_bill_fees_extract,
    build_recoupment_extract,
    poa_claim_payment_extract_lines,
)
from app.domain.reference_rules import ReferenceRules
from app.models.application.enums import (
    AddressSource,
    CorrespondenceRecipientType,
    MeritsDecision,
    ProceedingId,
    PublicBodyId,
)
from app.models.application.index import (
    Address,
    Application,
    ApplicationProceeding,
    ApplicationPublicBody,
    Client,
    CoronersLetter,
    Deceased,
    Provider,
)
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimStatus,
    ClaimType,
    InquestOutcomeCode,
    NumberOfCounselInstructed,
    POAType,
)
from app.models.claim.index import (
    Claim,
    ClaimCostTemplate,
    ClaimDecision,
    ClaimDecisionAmount,
    ClaimEvidence,
    ClaimInquestOutcome,
    ClaimPaymentExtract,
)
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent

SessionFactory = Callable[[], AbstractContextManager[Session]]

SEED_FIRM_CODE = "1473"
SEED_PROVIDER_EMAIL = "provider@example.com"
SEED_CLAIMANT_ID = "claimant-123@provider.co.uk"
SEED_CASEWORKER_NAME = "Seed Caseworker"
SEED_CASEWORKER_EMAIL = "seed.caseworker@example.com"
SEED_CASEWORKER_ENTRA_OBJECT_ID = "5eed0001-0000-4000-8000-000000000001"
SEED_CORONERS_LETTER_ID = uuid.UUID("5e0bb75e-00e8-4e3d-84b3-88b77ba3aad4")
SEED_FINAL_BILL_CORONERS_LETTER_ID = uuid.UUID("c3e4a5b6-7890-4cde-9f01-23456789abcd")
SEED_CLAIM_EVIDENCE_ID = uuid.UUID("7b34cf18-1d41-40eb-8bc8-9a2e7e14dea6")
SEED_FINAL_BILL_POA_CLAIM_EVIDENCE_ID = uuid.UUID(
    "d4f5a6b7-8901-4def-9012-3456789abcde"
)
SEED_FINAL_BILL_CLAIM_EVIDENCE_ID = uuid.UUID("a1c2e3f4-5678-4abc-9def-0123456789ab")
SEED_FINAL_BILL_COST_TEMPLATE_FILE_ID = uuid.UUID(
    "b2d3f4a5-6789-4bcd-8ef0-123456789abc"
)

CERTIFICATE_START_DATE = date(2025, 1, 1)

# Applications are submitted and granted days ago, then their claims follow.
APPLICATION_AGE = timedelta(days=3)
GRANT_DELAY = timedelta(hours=2)
ONE_SECOND = timedelta(seconds=1)
AUTO_APPROVAL_EMAIL_DELAY = timedelta(seconds=60)
FINAL_BILL_ASSESSMENT_DELAY = timedelta(seconds=120)

BULK_REFERENCE_ATTEMPTS = 10
BULK_FIRM_CODES = Config.SEED_DEV_FIRM_CODES or (SEED_FIRM_CODE,)

BULK_FIRST_NAMES = ["Test", "Sample", "Example", "Demo", "Dummy"]
BULK_LAST_NAMES = ["User", "Client", "Person", "Applicant", "Account"]

# POA claims that are small enough for the service to approve on submission.
BULK_PAID_POA_TEMPLATES = [
    {
        "poa_type": POAType.PROFIT_COST,
        "net": None,
        "gross": None,
        "vat_zero": Decimal("100.00"),
        "submission_offset_seconds": 279,
    },
    {
        "poa_type": POAType.PROFIT_COST,
        "net": Decimal("200.00"),
        "gross": Decimal("300.00"),
        "vat_zero": None,
        "submission_offset_seconds": 320,
    },
    {
        "poa_type": POAType.EXPERT_COST,
        "net": Decimal("0.00"),
        "gross": Decimal("0.00"),
        "vat_zero": Decimal("150.00"),
        "submission_offset_seconds": 342,
    },
    {
        "poa_type": POAType.NON_EXPERT_DISBURSEMENT,
        "net": Decimal("200.00"),
        "gross": Decimal("300.00"),
        "vat_zero": Decimal("0.00"),
        "submission_offset_seconds": 367,
    },
]
# Large enough that, with the approved claims above, the case cost limit is exceeded
# and the service holds the claim for a caseworker instead of approving it.
BULK_PENDING_POA_NET = Decimal("8250.00")
BULK_PENDING_POA_GROSS = Decimal("9900.00")
BULK_PENDING_POA_OFFSET_SECONDS = 420
BULK_FINAL_BILL_OFFSET_SECONDS = 460
BULK_FINAL_BILL_DECISION_AMOUNT = {
    "profit_cost_net": Decimal("5000.00"),
    "profit_cost_gross": Decimal("6000.00"),
    "disbursement_net": Decimal("5000.00"),
    "disbursement_gross": Decimal("7000.00"),
    "disbursement_vat_zero": Decimal("1000.00"),
}

# A POA the service approves on submission, which pushes the next POA over the case
# cost limit so that it awaits a caseworker.
NAMED_APPROVED_POA_NET = Decimal("7500.00")
NAMED_APPROVED_POA_GROSS = Decimal("9000.00")
NAMED_PENDING_POA_NET = Decimal("1000.00")
NAMED_PENDING_POA_GROSS = Decimal("1200.00")


@dataclass(frozen=True)
class _PoaClaimSpec:
    claim_reference: str
    poa_type: POAType
    net: Decimal | None
    gross: Decimal | None
    vat_zero: Decimal | None
    submitted_at: datetime
    approved: bool
    evidence_id: uuid.UUID | None = None
    evidence_sds_file_name: str = "seed-claim-evidence"
    evidence_file_name: str = "claim-evidence.pdf"


@dataclass(frozen=True)
class _FinalBillClaimSpec:
    claim_reference: str
    submitted_at: datetime
    paid: bool
    evidence_id: uuid.UUID | None = None
    evidence_sds_file_name: str = "seed-final-bill-claim-evidence"
    evidence_file_name: str = "final-bill-claim-evidence.pdf"
    cost_template_file_id: uuid.UUID | None = None


def _history_event(
    application_id: int,
    reference: HistoryEventReference,
    timestamp: datetime,
    actor_type: ActorType,
    actor: str | None = None,
    event_data: dict[str, Any] | None = None,
) -> HistoryEvent:
    """A history event as the services record it for each kind of actor."""
    if actor_type == ActorType.SYSTEM:
        return HistoryEvent(
            application_id=application_id,
            event_reference=reference,
            timestamp=timestamp,
            actor="System",
            actor_type=actor_type,
            event_data=event_data,
        )
    if actor_type == ActorType.CASEWORKER:
        return HistoryEvent(
            application_id=application_id,
            event_reference=reference,
            timestamp=timestamp,
            actor=SEED_CASEWORKER_NAME,
            actor_type=actor_type,
            entra_user_object_id=SEED_CASEWORKER_ENTRA_OBJECT_ID,
            actor_email_address=SEED_CASEWORKER_EMAIL,
            event_data=event_data,
        )
    return HistoryEvent(
        application_id=application_id,
        event_reference=reference,
        timestamp=timestamp,
        actor=actor,
        actor_type=actor_type,
        actor_email_address=actor,
        event_data=event_data,
    )


def _letter_address(address: Address, recipient_name: str | None) -> dict[str, Any]:
    line_1 = (
        f"c/o {recipient_name} {address.address_line_1}"
        if recipient_name
        else address.address_line_1
    )
    return {
        "address_line_1": line_1,
        "address_line_2": address.address_line_2,
        "town_or_city": address.town_or_city,
        "county": address.county,
        "postcode": address.postcode,
    }


def _create_granted_application(
    db_session: Session,
    *,
    laa_reference: str,
    coroners_letter: CoronersLetter,
    client_fields: dict[str, Any],
    correspondence_address: Address,
    home_address: Address,
    deceased_fields: dict[str, Any],
    provider: Provider,
    recipient_name: str | None,
    submitted_at: datetime,
) -> Application:
    """Persist an application as it looks once granted, with the history of getting
    there: submitted by the provider, confirmed, assessed, and the certificate sent."""
    granted_at = submitted_at + GRANT_DELAY
    db_session.add(coroners_letter)
    db_session.add_all([correspondence_address, home_address])
    db_session.flush()

    client = Client(
        **client_fields,
        has_applied_previously=False,
        correspondence_address_source=AddressSource.USE_SPECIFIED_ADDRESS,
        correspondence_address_id=correspondence_address.address_id,
        home_address_id=home_address.address_id,
        has_no_fixed_abode=False,
        correspondence_recipient_type=(
            CorrespondenceRecipientType.PERSON if recipient_name else None
        ),
        correspondence_recipient_name=recipient_name,
    )
    db_session.add(client)
    db_session.flush()

    deceased = Deceased(**deceased_fields, client_id=client.client_id)
    db_session.add(deceased)
    db_session.add(provider)
    db_session.flush()

    application = Application(
        client_id=client.client_id,
        deceased_id=deceased.deceased_id,
        provider_id=provider.provider_id,
        coroners_letter_id=coroners_letter.coroners_letter_id,
        proceeding=ApplicationProceeding(
            proceeding_id=ProceedingId.IQPC,
            merits_decision=MeritsDecision.GRANTED,
            certificate_start_date=CERTIFICATE_START_DATE,
            substantive_cost_limitation_effective_date=CERTIFICATE_START_DATE,
            certificate_issue_date=granted_at.date(),
        ),
        public_bodies=[
            ApplicationPublicBody(
                public_body_id=PublicBodyId.DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE
            )
        ],
        laa_reference=laa_reference,
        created_at=submitted_at,
        updated_at=granted_at,
    )
    db_session.add(application)
    db_session.flush()

    application_id = application.application_id
    provider_email = provider.email_address
    notification = {"recipient": provider_email, "channel": "email"}
    db_session.add_all(
        [
            _history_event(
                application_id,
                HistoryEventReference.APPLICATION_SUBMITTED,
                submitted_at,
                ActorType.PROVIDER,
                provider_email,
            ),
            _history_event(
                application_id,
                HistoryEventReference.APPLICATION_SUBMISSION_CONFIRMATION,
                submitted_at + ONE_SECOND,
                ActorType.SYSTEM,
                event_data=notification,
            ),
            _history_event(
                application_id,
                HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
                granted_at,
                ActorType.CASEWORKER,
                event_data={"merits_decision": "Granted"},
            ),
            _history_event(
                application_id,
                HistoryEventReference.CERTIFICATE_CREATED,
                granted_at + ONE_SECOND,
                ActorType.CASEWORKER,
                event_data={"laa_reference": laa_reference},
            ),
            _history_event(
                application_id,
                HistoryEventReference.APPLICATION_GRANTED_EMAIL,
                granted_at + 2 * ONE_SECOND,
                ActorType.SYSTEM,
                event_data=notification,
            ),
            _history_event(
                application_id,
                HistoryEventReference.APPLICATION_GRANTED_LETTER,
                granted_at + 3 * ONE_SECOND,
                ActorType.SYSTEM,
                event_data={
                    "recipient": _letter_address(
                        correspondence_address, recipient_name
                    ),
                    "channel": "letter",
                },
            ),
        ]
    )
    db_session.flush()
    return application


class _ClaimSeeder:
    """Seeds an application's claims in submission order, producing the states and
    history the services would: small POA claims are approved on submission, POA
    claims over the case cost limit wait for a caseworker, and final bills are
    always assessed by a caseworker."""

    def __init__(self, db_session: Session, application: Application) -> None:
        self.db_session = db_session
        self.application = application
        self.provider_email = application.provider.email_address
        self.cost_limit = application.proceeding.substantive_cost_limitation
        self.approved: list[ApprovedClaimAmount] = []
        self.paid_poa_extracts: list[RecoupmentSourceLine] = []

    def poa(self, spec: _PoaClaimSpec) -> Claim:
        claim = Claim(
            application_id=self.application.application_id,
            claim_reference=spec.claim_reference,
            claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
            status_id=(
                ClaimStatus.PAY_IN_FULL if spec.approved else ClaimStatus.SUBMITTED
            ),
            submission_date=spec.submitted_at,
            total_profit_cost_net=spec.net,
            total_profit_cost_gross=spec.gross,
            total_profit_cost_vat_zero=spec.vat_zero,
            total_funds_remaining_after_claim=self._funds_remaining_after(
                spec.gross, spec.vat_zero
            ),
            poa_type_id=spec.poa_type,
            claimant_id=SEED_CLAIMANT_ID,
            claim_evidence=[self._evidence(spec)],
        )
        self.db_session.add(claim)
        self.db_session.flush()
        self._record_submission(claim, spec.submitted_at)

        if spec.approved:
            approved_at = spec.submitted_at + 2 * ONE_SECOND
            decision_amounts = pay_in_full_claim_from_submitted_poa_claim(claim)
            lines = poa_claim_payment_extract_lines(claim, decision_amounts)
            self._pay_in_full(claim, decision_amounts, approved_at, lines)
            self.paid_poa_extracts.extend(
                RecoupmentSourceLine(
                    invoice_number=line.invoice_number,
                    invoice_amount=line.invoice_amount,
                    tax_code=line.tax_code,
                )
                for line in lines
            )
            self._record(
                HistoryEventReference.POA_AUTO_APPROVED,
                approved_at,
                ActorType.SYSTEM,
                event_data={"claim_reference": claim.claim_reference},
            )
            self._record(
                HistoryEventReference.CLAIM_APPROVED_EMAIL,
                spec.submitted_at + AUTO_APPROVAL_EMAIL_DELAY,
                ActorType.SYSTEM,
                event_data={"claim_reference": claim.claim_reference},
            )
        return claim

    def final_bill(self, spec: _FinalBillClaimSpec) -> Claim:
        claim = Claim(
            application_id=self.application.application_id,
            claim_reference=spec.claim_reference,
            claim_type_id=ClaimType.FINAL_BILL,
            status_id=(ClaimStatus.PAY_IN_FULL if spec.paid else ClaimStatus.SUBMITTED),
            submission_date=spec.submitted_at,
            total_profit_cost_net=None,
            total_profit_cost_gross=Decimal("1200.00"),
            total_profit_cost_vat_zero=None,
            total_funds_remaining_after_claim=self._funds_remaining_after(
                Decimal("1200.00"), None
            ),
            poa_type_id=None,
            has_counsel_been_paid=True,
            has_alternative_funding=False,
            has_recovery_costs_awarded=True,
            financial_recovery_previous_pre_certificate_costs=Decimal("100.00"),
            financial_recovery_cost=Decimal("200.00"),
            financial_recovery_damages=Decimal("300.00"),
            financial_recovery_interest=Decimal("50.00"),
            paying_party="Test Paying Party",
            number_of_counsel_instructed=NumberOfCounselInstructed.TWO,
            claimant_id=SEED_CLAIMANT_ID,
            claim_evidence=[self._evidence(spec)],
            claim_inquest_outcomes=[
                ClaimInquestOutcome(
                    inquest_outcome_id=InquestOutcomeCode.NATURAL_CAUSES
                )
            ],
            claim_cost_template=ClaimCostTemplate(
                claim_cost_template_file_id=(
                    spec.cost_template_file_id or uuid.uuid4()
                ),
                claim_cost_template_file_name="final_bill_costs.xlsx",
            ),
        )
        self.db_session.add(claim)
        self.db_session.flush()
        self._record_submission(claim, spec.submitted_at)

        if spec.paid:
            assessed_at = spec.submitted_at + FINAL_BILL_ASSESSMENT_DELAY
            decision_amounts = PayInFullClaim(
                claim_type_id=ClaimType.FINAL_BILL,
                **BULK_FINAL_BILL_DECISION_AMOUNT,
            )
            lines = self._final_bill_extract_lines(claim, decision_amounts, assessed_at)
            self._pay_in_full(claim, decision_amounts, assessed_at, lines)
            self._record(
                HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
                assessed_at,
                ActorType.CASEWORKER,
                event_data={
                    "claim_type": claim.claim_type_id.value,
                    "claim_reference": claim.claim_reference,
                    "claim_decision": ClaimStatus.PAY_IN_FULL.value,
                    "profit_cost_net": _amount(decision_amounts.profit_cost_net),
                    "profit_cost_gross": _amount(decision_amounts.profit_cost_gross),
                    "profit_cost_vat_zero": _amount(
                        decision_amounts.profit_cost_vat_zero
                    ),
                    "disbursement_net": _amount(decision_amounts.disbursement_net),
                    "disbursement_gross": _amount(decision_amounts.disbursement_gross),
                    "disbursement_vat_zero": _amount(
                        decision_amounts.disbursement_vat_zero
                    ),
                },
            )
            self._record(
                HistoryEventReference.CLAIM_FINAL_BILL_PAID_EMAIL,
                assessed_at + ONE_SECOND,
                ActorType.SYSTEM,
                event_data={"recipient": self.provider_email, "channel": "email"},
            )
        return claim

    def _funds_remaining_after(
        self, gross: Decimal | None, vat_zero: Decimal | None
    ) -> Decimal:
        funds_before = calculate_available_funds(self.cost_limit, self.approved)
        payment = ApprovedClaimAmount(None, gross, vat_zero).payment_amount
        return (funds_before - payment).quantize(Decimal("0.01"))

    @staticmethod
    def _evidence(spec: _PoaClaimSpec | _FinalBillClaimSpec) -> ClaimEvidence:
        values: dict[str, Any] = {
            "sds_file_name": spec.evidence_sds_file_name,
            "file_name": spec.evidence_file_name,
        }
        if spec.evidence_id is not None:
            values["claim_evidence_id"] = spec.evidence_id
        return ClaimEvidence(**values)

    def _record(
        self,
        reference: HistoryEventReference,
        timestamp: datetime,
        actor_type: ActorType,
        actor: str | None = None,
        event_data: dict[str, Any] | None = None,
    ) -> None:
        self.db_session.add(
            _history_event(
                self.application.application_id,
                reference,
                timestamp,
                actor_type,
                actor,
                event_data,
            )
        )

    def _record_submission(self, claim: Claim, submitted_at: datetime) -> None:
        self._record(
            HistoryEventReference.CLAIM_SUBMITTED,
            submitted_at,
            ActorType.PROVIDER,
            SEED_CLAIMANT_ID,
            {
                "claim_type": claim.claim_type_id.value,
                "claim_reference": claim.claim_reference,
            },
        )
        self._record(
            HistoryEventReference.CLAIM_SUBMISSION_CONFIRMATION,
            submitted_at + ONE_SECOND,
            ActorType.SYSTEM,
            event_data={"recipient": self.provider_email, "channel": "email"},
        )

    def _pay_in_full(
        self,
        claim: Claim,
        decision_amounts: PayInFullClaim,
        decided_at: datetime,
        extract_lines: list[PaymentExtractLine],
    ) -> None:
        decision_amounts.validate()
        decision = ClaimDecision(
            claim_id=claim.claim_id,
            decision=ClaimDecisionStatus.PAY_IN_FULL,
            created_at=decided_at,
        )
        self.db_session.add(decision)
        self.db_session.flush()
        self.db_session.add(
            ClaimDecisionAmount(
                claim_decision_id=decision.claim_decision_id,
                profit_cost_net=decision_amounts.profit_cost_net,
                profit_cost_gross=decision_amounts.profit_cost_gross,
                profit_cost_vat_zero=decision_amounts.profit_cost_vat_zero,
                disbursement_net=decision_amounts.disbursement_net,
                disbursement_gross=decision_amounts.disbursement_gross,
                disbursement_vat_zero=decision_amounts.disbursement_vat_zero,
            )
        )
        self.db_session.add_all(
            ClaimPaymentExtract(
                claim_id=claim.claim_id,
                sequence_number=line.sequence_number,
                invoice_number=line.invoice_number,
                invoice_amount=line.invoice_amount,
                invoice_date=line.invoice_date,
                invoice_type=line.invoice_type,
                tax_code=line.tax_code,
                created_at=decided_at,
            )
            for line in extract_lines
        )
        self.approved.append(
            ApprovedClaimAmount(
                ClaimDecisionStatus.PAY_IN_FULL,
                claim.total_profit_cost_gross,
                claim.total_profit_cost_vat_zero,
            )
        )

    def _final_bill_extract_lines(
        self, claim: Claim, decision_amounts: PayInFullClaim, decided_at: datetime
    ) -> list[PaymentExtractLine]:
        invoice_date = claim.submission_date.date()
        lines: list[PaymentExtractLine] = []
        fees_line = build_final_bill_fees_extract(
            claim_reference=claim.claim_reference,
            sequence=1,
            invoice_date=invoice_date,
            gross=decision_amounts.profit_cost_gross,
            vat_zero_amount=decision_amounts.profit_cost_vat_zero,
        )
        if fees_line is not None:
            lines.append(fees_line)
        lines.extend(
            build_final_bill_disbursement_extract(
                claim_reference=claim.claim_reference,
                start_sequence=len(lines) + 1,
                invoice_date=invoice_date,
                gross=decision_amounts.disbursement_gross,
                vat_zero_amount=decision_amounts.disbursement_vat_zero,
            )
        )
        lines.extend(
            build_recoupment_extract(
                start_sequence=len(lines) + 1,
                invoice_date=decided_at.date(),
                original_lines=self.paid_poa_extracts,
            )
        )
        return lines


def _amount(amount: Decimal | None) -> str | None:
    return str(amount) if amount is not None else None


def _named_party_fields() -> dict[str, dict[str, Any]]:
    return {
        "client_fields": {
            "client_first_name": "Jane",
            "client_last_name": "Smith",
            "client_last_name_at_birth": "Jones",
            "date_of_birth": "2000-01-01",
            "national_insurance_number": "AA123456A",
        },
        "deceased_fields": {
            "deceased_first_name": "John",
            "deceased_last_name": "Smith",
            "deceased_date_of_birth": "2000-01-01",
            "deceased_date_of_death": "2025-01-01",
            "coroners_reference": "Example reference number",
            "further_information": "Further information.",
            "client_relationship_to_deceased": "Spouse",
        },
    }


def _named_address() -> Address:
    return Address(
        address_line_1="123 Example Street",
        address_line_2="Flat 1",
        town_or_city="Example Town",
        county="Example County",
        postcode="AA1 1AA",
    )


def _named_application(
    db_session: Session,
    *,
    laa_reference: str,
    coroners_letter: CoronersLetter,
    now: datetime,
) -> Application:
    return _create_granted_application(
        db_session,
        laa_reference=laa_reference,
        coroners_letter=coroners_letter,
        **_named_party_fields(),
        correspondence_address=_named_address(),
        home_address=_named_address(),
        provider=Provider(
            firm_code=SEED_FIRM_CODE,
            office_id="0U651L",
            email_address=SEED_PROVIDER_EMAIL,
        ),
        recipient_name="Robert Jones",
        submitted_at=now - APPLICATION_AGE,
    )


def seed_dev(session_factory: SessionFactory = CustomSessionLocal):
    """
    Seeds a granted application with an approved and a submitted payment on account
    claim, plus a second granted application with an approved and a submitted payment
    on account claim and a submitted final bill claim (and their related records,
    including the history events each state implies) into the database.
    Idempotent: keyed on the seed coroners letter id, so it is safe to re-run.
    Rows from an earlier version of this seed are not updated: reset the database.
    """
    with session_factory() as db_session:
        if db_session.get(CoronersLetter, SEED_CORONERS_LETTER_ID) is not None:
            return

        now = datetime.now(UTC)

        poa_application = _named_application(
            db_session,
            laa_reference="INQ-YYY-YYY",
            coroners_letter=CoronersLetter(
                coroners_letter_id=SEED_CORONERS_LETTER_ID,
                sds_file_name="seed-coroners-letter",
                file_name="coroners-letter.pdf",
            ),
            now=now,
        )
        claims = _ClaimSeeder(db_session, poa_application)
        claims.poa(
            _PoaClaimSpec(
                claim_reference="INQC-YYYY-AAAA",
                poa_type=POAType.PROFIT_COST,
                net=NAMED_APPROVED_POA_NET,
                gross=NAMED_APPROVED_POA_GROSS,
                vat_zero=None,
                submitted_at=now - timedelta(minutes=20),
                approved=True,
                evidence_sds_file_name="seed-approved-claim-evidence",
                evidence_file_name="approved-claim-evidence.pdf",
            )
        )
        claims.poa(
            _PoaClaimSpec(
                claim_reference="INQC-YYYY-YYYY",
                poa_type=POAType.PROFIT_COST,
                net=NAMED_PENDING_POA_NET,
                gross=NAMED_PENDING_POA_GROSS,
                vat_zero=None,
                submitted_at=now - timedelta(minutes=10),
                approved=False,
                evidence_id=SEED_CLAIM_EVIDENCE_ID,
            )
        )

        final_bill_application = _named_application(
            db_session,
            laa_reference="INQ-XXX-XXX",
            coroners_letter=CoronersLetter(
                coroners_letter_id=SEED_FINAL_BILL_CORONERS_LETTER_ID,
                sds_file_name="seed-final-bill-coroners-letter",
                file_name="final-bill-coroners-letter.pdf",
            ),
            now=now,
        )
        claims = _ClaimSeeder(db_session, final_bill_application)
        claims.poa(
            _PoaClaimSpec(
                claim_reference="INQC-AAAA-AAAA",
                poa_type=POAType.PROFIT_COST,
                net=NAMED_APPROVED_POA_NET,
                gross=NAMED_APPROVED_POA_GROSS,
                vat_zero=None,
                submitted_at=now - timedelta(minutes=20),
                approved=True,
                evidence_sds_file_name="seed-final-bill-approved-poa-claim-evidence",
                evidence_file_name="final-bill-approved-poa-claim-evidence.pdf",
            )
        )
        claims.poa(
            _PoaClaimSpec(
                claim_reference="INQC-XXXX-XXXX",
                poa_type=POAType.PROFIT_COST,
                net=NAMED_PENDING_POA_NET,
                gross=NAMED_PENDING_POA_GROSS,
                vat_zero=None,
                submitted_at=now - timedelta(minutes=10),
                approved=False,
                evidence_id=SEED_FINAL_BILL_POA_CLAIM_EVIDENCE_ID,
                evidence_sds_file_name="seed-final-bill-poa-claim-evidence",
                evidence_file_name="final-bill-poa-claim-evidence.pdf",
            )
        )
        claims.final_bill(
            _FinalBillClaimSpec(
                claim_reference="INQC-FFFF-FFFF",
                submitted_at=now - timedelta(minutes=5),
                paid=False,
                evidence_id=SEED_FINAL_BILL_CLAIM_EVIDENCE_ID,
                cost_template_file_id=SEED_FINAL_BILL_COST_TEMPLATE_FILE_ID,
            )
        )
        db_session.commit()


def _random_reference(
    db_session, reference_rules, used_references, prefix, length, column
) -> str:
    for _ in range(BULK_REFERENCE_ATTEMPTS):
        parts = [
            "".join(
                random.choice(reference_rules.allowed_characters)  # nosec B311
                for _ in range(length)
            )
            for _ in range(2)
        ]
        reference = f"{prefix}-{parts[0]}-{parts[1]}"
        if (
            reference in used_references
            or reference_rules.contains_banned_word(reference.replace("-", ""))
            or db_session.scalar(select(exists().where(column == reference)))
        ):
            continue
        used_references.add(reference)
        return reference
    raise RuntimeError(f"Could not generate a unique {prefix} reference")


def _random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))  # nosec B311


def _random_office_id() -> str:
    digits = "".join(random.choices(string.digits, k=3))  # nosec B311
    return (
        f"{random.choice(string.digits)}"  # nosec B311
        f"{random.choice(string.ascii_uppercase)}"  # nosec B311
        f"{digits}"
        f"{random.choice(string.ascii_uppercase)}"  # nosec B311
    )


def _bulk_address() -> Address:
    return Address(
        address_line_1=f"{random.randint(1, 250)} Example Street",  # nosec B311
        address_line_2="Flat 1",
        town_or_city="Example Town",
        county="Example County",
        postcode="AA1 1AA",
    )


def _seed_bulk_claims(
    db_session, reference_rules, used_references, application, now: datetime
):
    base_submission_date = now - timedelta(minutes=10)
    claims = _ClaimSeeder(db_session, application)

    def claim_reference() -> str:
        return _random_reference(
            db_session,
            reference_rules,
            used_references,
            "INQC",
            4,
            Claim.claim_reference,
        )

    for template in BULK_PAID_POA_TEMPLATES:
        claims.poa(
            _PoaClaimSpec(
                claim_reference=claim_reference(),
                poa_type=template["poa_type"],
                net=template["net"],
                gross=template["gross"],
                vat_zero=template["vat_zero"],
                submitted_at=base_submission_date
                + timedelta(seconds=template["submission_offset_seconds"]),
                approved=True,
                evidence_sds_file_name="seed-bulk-claim-evidence",
            )
        )
    claims.poa(
        _PoaClaimSpec(
            claim_reference=claim_reference(),
            poa_type=POAType.PROFIT_COST,
            net=BULK_PENDING_POA_NET,
            gross=BULK_PENDING_POA_GROSS,
            vat_zero=None,
            submitted_at=base_submission_date
            + timedelta(seconds=BULK_PENDING_POA_OFFSET_SECONDS),
            approved=False,
            evidence_sds_file_name="seed-bulk-claim-evidence",
        )
    )
    claims.final_bill(
        _FinalBillClaimSpec(
            claim_reference=claim_reference(),
            submitted_at=base_submission_date
            + timedelta(seconds=BULK_FINAL_BILL_OFFSET_SECONDS),
            paid=True,
            evidence_sds_file_name="seed-bulk-claim-evidence",
            evidence_file_name="claim-evidence.pdf",
        )
    )


def _seed_bulk_application(db_session, reference_rules, used_references, now):
    first_name = random.choice(BULK_FIRST_NAMES)  # nosec B311
    last_name = random.choice(BULK_LAST_NAMES)  # nosec B311

    application = _create_granted_application(
        db_session,
        laa_reference=_random_reference(
            db_session,
            reference_rules,
            used_references,
            "INQ",
            3,
            Application.laa_reference,
        ),
        coroners_letter=CoronersLetter(
            coroners_letter_id=uuid.uuid4(),
            sds_file_name="seed-bulk-coroners-letter",
            file_name="coroners-letter.pdf",
        ),
        client_fields={
            "client_first_name": first_name,
            "client_last_name": last_name,
            "client_last_name_at_birth": last_name,
            "date_of_birth": _random_date(
                date(1950, 1, 1), date(2000, 12, 31)
            ).isoformat(),
            "national_insurance_number": "AA123456A",
        },
        correspondence_address=_bulk_address(),
        home_address=_bulk_address(),
        deceased_fields={
            "deceased_first_name": random.choice(BULK_FIRST_NAMES),  # nosec B311
            "deceased_last_name": last_name,
            "deceased_date_of_birth": _random_date(
                date(1940, 1, 1), date(2000, 12, 31)
            ).isoformat(),
            "deceased_date_of_death": _random_date(
                date(2024, 1, 1), date(2025, 12, 31)
            ).isoformat(),
            "coroners_reference": f"COR-{random.randint(10000, 99999)}",  # nosec B311
            "further_information": "Further information.",
            "client_relationship_to_deceased": "Spouse",
        },
        provider=Provider(
            firm_code=random.choice(BULK_FIRM_CODES),  # nosec B311
            office_id=_random_office_id(),
            email_address=SEED_PROVIDER_EMAIL,
        ),
        recipient_name=None,
        submitted_at=now - APPLICATION_AGE,
    )
    _seed_bulk_claims(db_session, reference_rules, used_references, application, now)


def seed_bulk_applications(
    count: int, session_factory: SessionFactory = CustomSessionLocal
):
    """
    Seeds `count` granted applications modelled on INQ-XXX-XXX, each with approved POA
    claims, a POA claim awaiting assessment and a paid final bill claim, their
    decisions, payment extract lines and history events, using random references.
    Not idempotent: every run adds `count` more applications.
    """
    if count <= 0:
        return
    reference_rules = ReferenceRules.from_file(Config.BANNED_WORDS_FILE_PATH)
    used_references: set[str] = set()
    with session_factory() as db_session:
        now = datetime.now(UTC)
        for _ in range(count):
            _seed_bulk_application(db_session, reference_rules, used_references, now)
        db_session.commit()


if __name__ == "__main__":
    seed_dev()
    seed_bulk_applications(Config.SEED_DEV_APPLICATION_COUNT)
