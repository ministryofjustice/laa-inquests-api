import os
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import random
import string
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlmodel import exists, select

from app.config import Config
from app.db import CustomSessionLocal
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
    InvoiceTypeCode,
    NumberOfCounselInstructed,
    POAType,
    TaxCode,
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

SEED_FIRM_CODE = "1473"
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

BULK_REFERENCE_ATTEMPTS = 10
BULK_FIRM_CODES = Config.SEED_DEV_FIRM_CODES or (SEED_FIRM_CODE,)

BULK_CLAIMANT_ID = "claimant-123@provider.co.uk"
BULK_FIRST_NAMES = ["Test", "Sample", "Example", "Demo", "Dummy"]
BULK_LAST_NAMES = ["User", "Client", "Person", "Applicant", "Account"]

BULK_PAID_POA_TEMPLATES = [
    {
        "poa_type_id": POAType.PROFIT_COST,
        "total_profit_cost_net": None,
        "total_profit_cost_gross": None,
        "total_profit_cost_vat_zero": Decimal("100.00"),
        "total_funds_remaining_after_claim": Decimal("9900.00"),
        "submission_offset_seconds": 279,
        "decision_amount": {"profit_cost_vat_zero": Decimal("100.00")},
        "extract_amount": Decimal("80.00"),
        "tax_code": TaxCode.ZERO_VAT,
    },
    {
        "poa_type_id": POAType.PROFIT_COST,
        "total_profit_cost_net": Decimal("200.00"),
        "total_profit_cost_gross": Decimal("300.00"),
        "total_profit_cost_vat_zero": None,
        "total_funds_remaining_after_claim": Decimal("9600.00"),
        "submission_offset_seconds": 320,
        "decision_amount": {
            "profit_cost_net": Decimal("200.00"),
            "profit_cost_gross": Decimal("300.00"),
        },
        "extract_amount": Decimal("192.00"),
        "tax_code": TaxCode.GB_VAT_20,
    },
    {
        "poa_type_id": POAType.EXPERT_COST,
        "total_profit_cost_net": Decimal("0.00"),
        "total_profit_cost_gross": Decimal("0.00"),
        "total_profit_cost_vat_zero": Decimal("150.00"),
        "total_funds_remaining_after_claim": Decimal("9600.00"),
        "submission_offset_seconds": 342,
        "decision_amount": {
            "disbursement_net": Decimal("0.00"),
            "disbursement_gross": Decimal("0.00"),
            "disbursement_vat_zero": Decimal("150.00"),
        },
        "extract_amount": Decimal("150.00"),
        "tax_code": TaxCode.ZERO_VAT,
    },
    {
        "poa_type_id": POAType.NON_EXPERT_DISBURSEMENT,
        "total_profit_cost_net": Decimal("200.00"),
        "total_profit_cost_gross": Decimal("300.00"),
        "total_profit_cost_vat_zero": Decimal("0.00"),
        "total_funds_remaining_after_claim": Decimal("9300.00"),
        "submission_offset_seconds": 367,
        "decision_amount": {
            "disbursement_net": Decimal("200.00"),
            "disbursement_gross": Decimal("300.00"),
            "disbursement_vat_zero": Decimal("0.00"),
        },
        "extract_amount": Decimal("300.00"),
        "tax_code": TaxCode.GB_VAT_20,
    },
]
BULK_FINAL_BILL_DECISION_AMOUNT = {
    "profit_cost_net": Decimal("5000.00"),
    "profit_cost_gross": Decimal("6000.00"),
    "disbursement_net": Decimal("5000.00"),
    "disbursement_gross": Decimal("7000.00"),
    "disbursement_vat_zero": Decimal("1000.00"),
}
BULK_FINAL_BILL_EXTRACT_LINES = [
    (Decimal("6000.00"), InvoiceTypeCode.FINAL_BILL_FEES, TaxCode.GB_VAT_20),
    (Decimal("6000.00"), InvoiceTypeCode.FINAL_BILL_DISBURSEMENT, TaxCode.GB_VAT_20),
    (Decimal("1000.00"), InvoiceTypeCode.FINAL_BILL_DISBURSEMENT, TaxCode.ZERO_VAT),
]


def seed_dev():
    """
    Seeds a granted application with a submitted payment on account claim, plus a
    second granted application with a submitted final bill claim (and their related
    records) into the database.
    Idempotent: keyed on the seed coroners letter id, so it is safe to re-run.
    """
    with CustomSessionLocal() as db_session:
        if db_session.get(CoronersLetter, SEED_CORONERS_LETTER_ID) is not None:
            return

        coroners_letter = CoronersLetter(
            coroners_letter_id=SEED_CORONERS_LETTER_ID,
            sds_file_name="seed-coroners-letter",
            file_name="coroners-letter.pdf",
        )
        db_session.add(coroners_letter)

        correspondence_address = Address(
            address_line_1="123 Example Street",
            address_line_2="Flat 1",
            town_or_city="Example Town",
            county="Example County",
            postcode="AA1 1AA",
        )
        home_address = Address(
            address_line_1="123 Example Street",
            address_line_2="Flat 1",
            town_or_city="Example Town",
            county="Example County",
            postcode="AA1 1AA",
        )
        db_session.add(correspondence_address)
        db_session.add(home_address)
        db_session.flush()

        client = Client(
            client_first_name="Jane",
            client_last_name="Smith",
            client_last_name_at_birth="Jones",
            date_of_birth="2000-01-01",
            national_insurance_number="AA123456A",
            has_applied_previously=False,
            prev_application_reference="TBD",
            correspondence_address_source=AddressSource.USE_SPECIFIED_ADDRESS,
            correspondence_address_id=correspondence_address.address_id,
            home_address_id=home_address.address_id,
            has_no_fixed_abode=False,
            is_client_correspondence_recipient=False,
            correspondence_recipient_type=CorrespondenceRecipientType.PERSON,
            correspondence_recipient_name="string",
        )
        db_session.add(client)
        db_session.flush()

        deceased = Deceased(
            deceased_first_name="John",
            deceased_last_name="Smith",
            deceased_date_of_birth="2000-01-01",
            deceased_date_of_death="2025-01-01",
            coroners_reference="Example reference number",
            further_information="Further information.",
            client_relationship_to_deceased="Spouse",
            client_id=client.client_id,
        )
        db_session.add(deceased)
        db_session.flush()

        provider = Provider(
            firm_code=SEED_FIRM_CODE,
            office_id="0U651L",
            email_address="provider@example.com",
        )
        db_session.add(provider)
        db_session.flush()

        application_proceeding = ApplicationProceeding(
            proceeding_id=ProceedingId.IQPC,
            merits_decision=MeritsDecision.GRANTED,
            certificate_start_date=date(2025, 1, 1),
            certificate_issue_date=datetime.now(UTC).date(),
        )
        public_bodies = [
            ApplicationPublicBody(
                public_body_id=PublicBodyId.DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE
            )
        ]

        application = Application(
            client_id=client.client_id,
            deceased_id=deceased.deceased_id,
            provider_id=provider.provider_id,
            coroners_letter_id=SEED_CORONERS_LETTER_ID,
            proceeding=application_proceeding,
            public_bodies=public_bodies,
            laa_reference="INQ-YYY-YYY",
        )

        db_session.add(application)
        db_session.flush()

        claim = Claim(
            application_id=application.application_id,
            claim_reference="INQC-YYYY-YYYY",
            claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
            status_id=ClaimStatus.SUBMITTED,
            total_profit_cost_net=Decimal("1000.00"),
            total_profit_cost_gross=Decimal("1200.00"),
            total_profit_cost_vat_zero=Decimal("500.00"),
            poa_type_id=POAType.PROFIT_COST,
            claimant_id="claimant-123@provider.co.uk",
            claim_evidence=[
                ClaimEvidence(
                    claim_evidence_id=SEED_CLAIM_EVIDENCE_ID,
                    sds_file_name="seed-claim-evidence",
                    file_name="claim-evidence.pdf",
                )
            ],
        )
        db_session.add(claim)

        final_bill_coroners_letter = CoronersLetter(
            coroners_letter_id=SEED_FINAL_BILL_CORONERS_LETTER_ID,
            sds_file_name="seed-final-bill-coroners-letter",
            file_name="final-bill-coroners-letter.pdf",
        )
        db_session.add(final_bill_coroners_letter)

        final_bill_correspondence_address = Address(
            address_line_1="123 Example Street",
            address_line_2="Jones",
            town_or_city="Example Town",
            county="Jones",
            postcode="AA1 1AA",
        )
        final_bill_home_address = Address(
            address_line_1="123 Example Street",
            address_line_2="Jones",
            town_or_city="Example Town",
            county="Jones",
            postcode="AA1 1AA",
        )
        db_session.add(final_bill_correspondence_address)
        db_session.add(final_bill_home_address)
        db_session.flush()

        final_bill_client = Client(
            client_first_name="Jane",
            client_last_name="Smith",
            client_last_name_at_birth="Jones",
            date_of_birth="2000-01-01",
            national_insurance_number="AA123456A",
            has_applied_previously=False,
            prev_application_reference="TBD",
            correspondence_address_source=AddressSource.USE_SPECIFIED_ADDRESS,
            correspondence_address_id=final_bill_correspondence_address.address_id,
            home_address_id=final_bill_home_address.address_id,
            has_no_fixed_abode=False,
            is_client_correspondence_recipient=False,
            correspondence_recipient_type=CorrespondenceRecipientType.PERSON,
            correspondence_recipient_name="string",
        )
        db_session.add(final_bill_client)
        db_session.flush()

        final_bill_deceased = Deceased(
            deceased_first_name="John",
            deceased_last_name="Smith",
            deceased_date_of_birth="2000-01-01",
            deceased_date_of_death="2025-01-01",
            coroners_reference="Example reference number",
            further_information="Further information.",
            client_relationship_to_deceased="Spouse",
            client_id=final_bill_client.client_id,
        )
        db_session.add(final_bill_deceased)
        db_session.flush()

        final_bill_provider = Provider(
            firm_code=SEED_FIRM_CODE,
            office_id="0U651L",
            email_address="provider@example.com",
        )
        db_session.add(final_bill_provider)
        db_session.flush()

        final_bill_application_proceeding = ApplicationProceeding(
            proceeding_id=ProceedingId.IQPC,
            merits_decision=MeritsDecision.GRANTED,
            certificate_start_date=date(2025, 1, 1),
            certificate_issue_date=datetime.now(UTC).date(),
        )
        final_bill_public_bodies = [
            ApplicationPublicBody(
                public_body_id=PublicBodyId.DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE
            )
        ]

        final_bill_application = Application(
            client_id=final_bill_client.client_id,
            deceased_id=final_bill_deceased.deceased_id,
            provider_id=final_bill_provider.provider_id,
            coroners_letter_id=SEED_FINAL_BILL_CORONERS_LETTER_ID,
            proceeding=final_bill_application_proceeding,
            public_bodies=final_bill_public_bodies,
            laa_reference="INQ-XXX-XXX",
        )

        db_session.add(final_bill_application)
        db_session.flush()

        final_bill_poa_claim = Claim(
            application_id=final_bill_application.application_id,
            claim_reference="INQC-XXXX-XXXX",
            claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
            status_id=ClaimStatus.SUBMITTED,
            total_profit_cost_net=Decimal("1000.00"),
            total_profit_cost_gross=Decimal("1200.00"),
            total_profit_cost_vat_zero=Decimal("500.00"),
            poa_type_id=POAType.PROFIT_COST,
            claimant_id="claimant-123@provider.co.uk",
            claim_evidence=[
                ClaimEvidence(
                    claim_evidence_id=SEED_FINAL_BILL_POA_CLAIM_EVIDENCE_ID,
                    sds_file_name="seed-final-bill-poa-claim-evidence",
                    file_name="final-bill-poa-claim-evidence.pdf",
                )
            ],
        )
        db_session.add(final_bill_poa_claim)

        final_bill_claim = Claim(
            application_id=final_bill_application.application_id,
            claim_reference="INQC-FBIL-0001",
            claim_type_id=ClaimType.FINAL_BILL,
            status_id=ClaimStatus.SUBMITTED,
            total_profit_cost_net=None,
            total_profit_cost_gross=Decimal("1200.00"),
            total_profit_cost_vat_zero=None,
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
            claimant_id="claimant-123@provider.co.uk",
            claim_evidence=[
                ClaimEvidence(
                    claim_evidence_id=SEED_FINAL_BILL_CLAIM_EVIDENCE_ID,
                    sds_file_name="seed-final-bill-claim-evidence",
                    file_name="final-bill-claim-evidence.pdf",
                )
            ],
            claim_inquest_outcomes=[
                ClaimInquestOutcome(
                    inquest_outcome_id=InquestOutcomeCode.NATURAL_CAUSES
                )
            ],
            claim_cost_template=ClaimCostTemplate(
                claim_cost_template_file_id=SEED_FINAL_BILL_COST_TEMPLATE_FILE_ID,
                claim_cost_template_file_name="final_bill_costs.xlsx",
            ),
        )
        db_session.add(final_bill_claim)
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
    return start + timedelta(days=random.randint(0, (end - start).days))


def _random_office_id() -> str:
    digits = "".join(random.choices(string.digits, k=3))
    return (
        f"{random.choice(string.digits)}"
        f"{random.choice(string.ascii_uppercase)}"
        f"{digits}"
        f"{random.choice(string.ascii_uppercase)}"
    )


def _bulk_address() -> Address:
    return Address(
        address_line_1=f"{random.randint(1, 250)} Example Street",
        address_line_2="Flat 1",
        town_or_city="Example Town",
        county="Example County",
        postcode="AA1 1AA",
    )


def _bulk_evidence() -> list[ClaimEvidence]:
    return [
        ClaimEvidence(
            sds_file_name="seed-bulk-claim-evidence", file_name="claim-evidence.pdf"
        )
    ]


def _seed_bulk_claims(db_session, reference_rules, used_references, application_id):
    base_submission_date = datetime.now(UTC) - timedelta(minutes=10)
    invoice_date = datetime.now(UTC).date()

    def claim_reference() -> str:
        return _random_reference(
            db_session,
            reference_rules,
            used_references,
            "INQC",
            4,
            Claim.claim_reference,
        )

    submitted_poa_claim = Claim(
        application_id=application_id,
        claim_reference=claim_reference(),
        claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
        status_id=ClaimStatus.SUBMITTED,
        submission_date=base_submission_date,
        total_profit_cost_net=Decimal("1000.00"),
        total_profit_cost_gross=Decimal("1200.00"),
        total_profit_cost_vat_zero=Decimal("500.00"),
        total_funds_remaining_after_claim=Decimal("10000.00"),
        poa_type_id=POAType.PROFIT_COST,
        claimant_id=BULK_CLAIMANT_ID,
        claim_evidence=_bulk_evidence(),
    )
    final_bill_claim = Claim(
        application_id=application_id,
        claim_reference=claim_reference(),
        claim_type_id=ClaimType.FINAL_BILL,
        status_id=ClaimStatus.PAY_IN_FULL,
        submission_date=base_submission_date,
        total_profit_cost_gross=Decimal("1200.00"),
        total_funds_remaining_after_claim=Decimal("10000.00"),
        has_counsel_been_paid=True,
        has_alternative_funding=False,
        has_recovery_costs_awarded=True,
        financial_recovery_previous_pre_certificate_costs=Decimal("100.00"),
        financial_recovery_cost=Decimal("200.00"),
        financial_recovery_damages=Decimal("300.00"),
        financial_recovery_interest=Decimal("50.00"),
        paying_party="Test Paying Party",
        number_of_counsel_instructed=NumberOfCounselInstructed.TWO,
        claimant_id=BULK_CLAIMANT_ID,
        claim_evidence=_bulk_evidence(),
        claim_inquest_outcomes=[
            ClaimInquestOutcome(inquest_outcome_id=InquestOutcomeCode.NATURAL_CAUSES)
        ],
        claim_cost_template=ClaimCostTemplate(
            claim_cost_template_file_id=uuid.uuid4(),
            claim_cost_template_file_name="final_bill_costs.xlsx",
        ),
    )
    paid_poa_claims = [
        Claim(
            application_id=application_id,
            claim_reference=claim_reference(),
            claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
            status_id=ClaimStatus.PAY_IN_FULL,
            submission_date=base_submission_date
            + timedelta(seconds=template["submission_offset_seconds"]),
            total_profit_cost_net=template["total_profit_cost_net"],
            total_profit_cost_gross=template["total_profit_cost_gross"],
            total_profit_cost_vat_zero=template["total_profit_cost_vat_zero"],
            total_funds_remaining_after_claim=template[
                "total_funds_remaining_after_claim"
            ],
            poa_type_id=template["poa_type_id"],
            claimant_id=BULK_CLAIMANT_ID,
            claim_evidence=_bulk_evidence(),
        )
        for template in BULK_PAID_POA_TEMPLATES
    ]
    db_session.add_all([submitted_poa_claim, final_bill_claim, *paid_poa_claims])
    db_session.flush()

    decision_amounts = [(final_bill_claim, BULK_FINAL_BILL_DECISION_AMOUNT)] + [
        (claim, template["decision_amount"])
        for claim, template in zip(paid_poa_claims, BULK_PAID_POA_TEMPLATES)
    ]
    for claim, amount in decision_amounts:
        decision = ClaimDecision(
            claim_id=claim.claim_id, decision=ClaimDecisionStatus.PAY_IN_FULL
        )
        db_session.add(decision)
        db_session.flush()
        db_session.add(
            ClaimDecisionAmount(claim_decision_id=decision.claim_decision_id, **amount)
        )

    for claim, template in zip(paid_poa_claims, BULK_PAID_POA_TEMPLATES):
        db_session.add(
            ClaimPaymentExtract(
                claim_id=claim.claim_id,
                sequence_number=1,
                invoice_number=f"{claim.claim_reference}_001",
                invoice_amount=template["extract_amount"],
                invoice_date=invoice_date,
                invoice_type=InvoiceTypeCode.POA,
                tax_code=template["tax_code"],
            )
        )

    final_bill_lines = [
        (f"{final_bill_claim.claim_reference}_{sequence:03d}", *line)
        for sequence, line in enumerate(BULK_FINAL_BILL_EXTRACT_LINES, start=1)
    ] + [
        (
            f"{claim.claim_reference}_001-R",
            -template["extract_amount"],
            InvoiceTypeCode.RECOUPED,
            template["tax_code"],
        )
        for claim, template in zip(paid_poa_claims, BULK_PAID_POA_TEMPLATES)
    ]
    for sequence, (invoice_number, amount, invoice_type, tax_code) in enumerate(
        final_bill_lines, start=1
    ):
        db_session.add(
            ClaimPaymentExtract(
                claim_id=final_bill_claim.claim_id,
                sequence_number=sequence,
                invoice_number=invoice_number,
                invoice_amount=amount,
                invoice_date=invoice_date,
                invoice_type=invoice_type,
                tax_code=tax_code,
            )
        )


def _seed_bulk_application(db_session, reference_rules, used_references):
    first_name = random.choice(BULK_FIRST_NAMES)  # nosec B311
    last_name = random.choice(BULK_LAST_NAMES)  # nosec B311

    correspondence_address = _bulk_address()
    home_address = _bulk_address()
    db_session.add_all([correspondence_address, home_address])
    db_session.flush()

    client = Client(
        client_first_name=first_name,
        client_last_name=last_name,
        client_last_name_at_birth=last_name,
        date_of_birth=_random_date(date(1950, 1, 1), date(2000, 12, 31)).isoformat(),
        national_insurance_number="AA123456A",
        has_applied_previously=False,
        prev_application_reference="TBD",
        correspondence_address_source=AddressSource.USE_SPECIFIED_ADDRESS,
        correspondence_address_id=correspondence_address.address_id,
        home_address_id=home_address.address_id,
        has_no_fixed_abode=False,
        is_client_correspondence_recipient=False,
        correspondence_recipient_type=CorrespondenceRecipientType.PERSON,
        correspondence_recipient_name="string",
    )
    db_session.add(client)
    db_session.flush()

    deceased = Deceased(
        deceased_first_name=random.choice(BULK_FIRST_NAMES),  # nosec B311
        deceased_last_name=last_name,
        deceased_date_of_birth=_random_date(
            date(1940, 1, 1), date(2000, 12, 31)
        ).isoformat(),
        deceased_date_of_death=_random_date(
            date(2024, 1, 1), date(2025, 12, 31)
        ).isoformat(),
        coroners_reference=f"COR-{random.randint(10000, 99999)}",  # nosec B311
        further_information="Further information.",
        client_relationship_to_deceased="Spouse",
        client_id=client.client_id,
    )
    db_session.add(deceased)

    provider = Provider(
        firm_code=random.choice(BULK_FIRM_CODES),  # nosec B311
        office_id=_random_office_id(),
        email_address="provider@example.com",
    )
    db_session.add(provider)

    coroners_letter = CoronersLetter(
        coroners_letter_id=uuid.uuid4(),
        sds_file_name="seed-bulk-coroners-letter",
        file_name="coroners-letter.pdf",
    )
    db_session.add(coroners_letter)
    db_session.flush()

    application = Application(
        client_id=client.client_id,
        deceased_id=deceased.deceased_id,
        provider_id=provider.provider_id,
        coroners_letter_id=coroners_letter.coroners_letter_id,
        proceeding=ApplicationProceeding(
            proceeding_id=ProceedingId.IQPC,
            merits_decision=MeritsDecision.GRANTED,
            certificate_start_date=date(2025, 1, 1),
            certificate_issue_date=datetime.now(UTC).date(),
        ),
        public_bodies=[
            ApplicationPublicBody(
                public_body_id=PublicBodyId.DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE
            )
        ],
        laa_reference=_random_reference(
            db_session,
            reference_rules,
            used_references,
            "INQ",
            3,
            Application.laa_reference,
        ),
    )
    db_session.add(application)
    db_session.flush()

    _seed_bulk_claims(
        db_session, reference_rules, used_references, application.application_id
    )


def seed_bulk_applications(count: int):
    """
    Seeds `count` granted applications modelled on INQ-XXX-XXX, each with its POA and
    final bill claims, decisions and payment extract lines, using random references.
    Not idempotent: every run adds `count` more applications.
    """
    if count <= 0:
        return
    reference_rules = ReferenceRules.from_file(Config.BANNED_WORDS_FILE_PATH)
    used_references: set[str] = set()
    with CustomSessionLocal() as db_session:
        for _ in range(count):
            _seed_bulk_application(db_session, reference_rules, used_references)
        db_session.commit()


if __name__ == "__main__":
    seed_dev()
    seed_bulk_applications(Config.SEED_DEV_APPLICATION_COUNT)
