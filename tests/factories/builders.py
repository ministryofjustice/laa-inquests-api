"""Single source of default values for every test data object.

``build_*`` returns an unsaved object. With ``for_db=True`` surrogate ids are left to the
database and the Proceeding/PublicBody reference rows (seeded by the ``session`` fixture)
are referenced by id rather than re-created.
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from itertools import count

from app.domain.constants.claims import SUBSTANTIVE_CERTIFICATE_AMOUNT
from app.models.application.certificate import ApplicationCertificate
from app.models.application.enums import (
    AddressSource,
    CorrespondenceRecipientType,
    MeritsDecision,
)
from app.models.application.index import (
    Address,
    Application,
    ApplicationProceeding,
    ApplicationPublicBody,
    Client,
    CoronersLetter,
    Deceased,
    Proceeding,
    ProceedingId,
    Provider,
    PublicBody,
    PublicBodyId,
)
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimStatus,
    ClaimType,
    InquestOutcomeCode,
    InvoiceTypeCode,
    POAType,
    ReasonCode,
    TaxCode,
)
from app.models.claim.index import (
    Claim,
    ClaimCostTemplate,
    ClaimDecision,
    ClaimEvidence,
    ClaimInquestOutcome,
    ClaimPaymentExtract,
    DecisionReason,
)
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent

# Distinguishes "not provided" from an explicit None.
UNSET = object()

DEFAULT_SUBMISSION_DATE = datetime(2026, 1, 1, tzinfo=UTC)

_laa_reference_sequence = count(1)
_claim_reference_sequence = count(1)


def next_laa_reference() -> str:
    n = next(_laa_reference_sequence)
    return f"INQ-{n // 1000:03d}-{n % 1000:03d}"


def next_claim_reference() -> str:
    n = next(_claim_reference_sequence)
    return f"INQC-{n // 10_000:04d}-{n % 10_000:04d}"


def _ids(for_db: bool, **ids) -> dict:
    return {} if for_db else ids


# --- Addresses -------------------------------------------------------------


def build_home_address(*, for_db: bool = False, **overrides) -> Address:
    defaults = {
        **_ids(for_db, address_id=1),
        "address_line_1": "123 Main St",
        "address_line_2": "Apt 4B",
        "town_or_city": "London",
        "county": "Greater London",
        "postcode": "SW1A 1AA",
    }
    return Address(**(defaults | overrides))


def build_correspondence_address(*, for_db: bool = False, **overrides) -> Address:
    defaults = {
        **_ids(for_db, address_id=2),
        "address_line_1": "456 Oak Ave",
        "town_or_city": "Manchester",
        "county": "Greater Manchester",
        "postcode": "M1 1AA",
    }
    return Address(**(defaults | overrides))


def build_office_address(*, for_db: bool = False, **overrides) -> Address:
    defaults = {
        **_ids(for_db, address_id=3),
        "address_line_1": "123 Main St",
        "address_line_2": "Apt 4B",
        "town_or_city": "London",
        "county": "Greater London",
        "postcode": "SW1A 1AA",
    }
    return Address(**(defaults | overrides))


# --- Application tree ------------------------------------------------------


def build_client(
    *,
    for_db: bool = False,
    home_address=UNSET,
    correspondence_address=UNSET,
    correspondence_recipient_name=UNSET,
    correspondence_recipient_type=UNSET,
    **overrides,
) -> Client:
    if home_address is UNSET:
        home_address = build_home_address(for_db=for_db)
    if correspondence_address is UNSET:
        correspondence_address = build_correspondence_address(for_db=for_db)

    if (
        correspondence_recipient_name is UNSET
        and correspondence_recipient_type is UNSET
    ):
        correspondence_recipient_name = None
        correspondence_recipient_type = None
    elif (
        correspondence_recipient_name is not UNSET
        and correspondence_recipient_type is UNSET
    ):
        correspondence_recipient_type = CorrespondenceRecipientType.PERSON
    elif (
        correspondence_recipient_name is UNSET
        and correspondence_recipient_type is not UNSET
    ):
        correspondence_recipient_name = "Recipient Name"

    defaults = {
        **_ids(for_db, client_id=1, home_address_id=1, correspondence_address_id=2),
        "client_first_name": "Jane",
        "client_last_name": "Doe",
        "client_last_name_at_birth": "Smith",
        "date_of_birth": "15-06-1985",
        "national_insurance_number": "AB123456C",
        "has_applied_previously": True,
        "prev_application_reference": "LAA-2024-001",
        "correspondence_address_source": AddressSource.USE_CLIENT_HOME_ADDRESS,
        "home_address": home_address,
        "correspondence_address": correspondence_address,
        "correspondence_recipient_type": correspondence_recipient_type,
        "correspondence_recipient_name": correspondence_recipient_name,
    }
    return Client(**(defaults | overrides))


def build_deceased(*, for_db: bool = False, **overrides) -> Deceased:
    defaults = {
        **_ids(for_db, deceased_id=1, client_id=1),
        "deceased_first_name": "Robert",
        "deceased_last_name": "Johnson",
        "deceased_date_of_birth": "01-01-1950",
        "deceased_date_of_death": "31-12-2025",
        "coroners_reference": "COR-2025-123",
        "further_information": "Additional context",
        "client_relationship_to_deceased": "Son",
    }
    return Deceased(**(defaults | overrides))


def build_provider(*, for_db: bool = False, **overrides) -> Provider:
    defaults = {
        **_ids(for_db, provider_id=1),
        "firm_code": "ABC123",
        "office_id": "0U651L",
        "email_address": "provider@example.com",
    }
    return Provider(**(defaults | overrides))


def build_proceeding(*, for_db: bool = False, **overrides) -> Proceeding:
    """Reference data; in the database it is seeded once per session."""
    defaults = {
        **_ids(for_db, id=1),
        "proceeding_id": ProceedingId.IQOT,
        "proceeding_name": "Inquest into death",
        "proceeding_description": "Inquest into death",
        "matter_type": "INQUESTS",
    }
    return Proceeding(**(defaults | overrides))


def build_public_body(**overrides) -> PublicBody:
    """Reference data; in the database it is seeded once per session."""
    defaults = {
        "id": 1,
        "public_body_id": PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
        "public_body_description": "Department for Transport",
    }
    return PublicBody(**(defaults | overrides))


def build_application_proceeding(
    *, for_db: bool = False, proceeding=UNSET, **overrides
) -> ApplicationProceeding:
    defaults = {
        **_ids(for_db, application_proceeding_id=1, application_id=12345),
        "proceeding_id": ProceedingId.IQOT,
        "merits_decision": MeritsDecision.PENDING,
        "certificate_start_date": datetime(2026, 6, 18, tzinfo=UTC),
        "certificate_issue_date": datetime(2026, 6, 18, tzinfo=UTC),
        "substantive_cost_limitation_effective_date": datetime(2026, 6, 18, tzinfo=UTC),
        "certificate_end_date": None,
    }
    if not for_db:
        defaults["proceeding"] = (
            build_proceeding() if proceeding is UNSET else proceeding
        )
    return ApplicationProceeding(**(defaults | overrides))


def build_application_public_body(
    *, for_db: bool = False, public_body=UNSET, **overrides
) -> ApplicationPublicBody:
    defaults = {
        **_ids(for_db, application_public_body_id=1, application_id=12345),
        "public_body_id": PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
    }
    if not for_db:
        defaults["public_body"] = (
            build_public_body() if public_body is UNSET else public_body
        )
    return ApplicationPublicBody(**(defaults | overrides))


def build_coroners_letter(**overrides) -> CoronersLetter:
    defaults = {"sds_file_name": "test_sds_file.pdf", "file_name": "test_file.pdf"}
    return CoronersLetter(**(defaults | overrides))


def build_application(
    *,
    for_db: bool = False,
    client=UNSET,
    deceased=UNSET,
    provider=UNSET,
    proceeding=UNSET,
    public_bodies=UNSET,
    client_overrides: dict | None = None,
    deceased_overrides: dict | None = None,
    provider_overrides: dict | None = None,
    proceeding_overrides: dict | None = None,
    **overrides,
) -> Application:
    """Build a full application aggregate.

    Nested objects can be replaced wholesale (``client=...``) or tweaked through the
    matching ``*_overrides`` dict. Remaining kwargs apply to the Application itself.
    """
    if client is UNSET:
        client = build_client(for_db=for_db, **(client_overrides or {}))
    if deceased is UNSET:
        deceased = build_deceased(for_db=for_db, **(deceased_overrides or {}))
    if provider is UNSET:
        provider = build_provider(for_db=for_db, **(provider_overrides or {}))
    if proceeding is UNSET:
        proceeding = build_application_proceeding(
            for_db=for_db, **(proceeding_overrides or {})
        )
    if public_bodies is UNSET:
        public_bodies = [build_application_public_body(for_db=for_db)]
    if for_db:
        deceased.client = client  # FK is resolved by SQLAlchemy at flush

    defaults = {
        **_ids(for_db, application_id=12345, client_id=1, deceased_id=1, provider_id=1),
        "laa_reference": next_laa_reference() if for_db else "INQ-YYY-YYY",
        "client": client,
        "deceased": deceased,
        "provider": provider,
        "proceeding": proceeding,
        "public_bodies": public_bodies,
    }
    return Application(**(defaults | overrides))


# --- Claims ----------------------------------------------------------------


def build_granted_application(
    *,
    substantive_cost_limitation: int = SUBSTANTIVE_CERTIFICATE_AMOUNT,
    certificate_start_date: date | None = None,
    **overrides,
) -> Application:
    """Application whose proceeding is granted with the given cost limit."""
    return build_application(
        proceeding_overrides={
            "merits_decision": MeritsDecision.GRANTED,
            "certificate_start_date": certificate_start_date,
            "proceeding": build_proceeding(
                substantive_cost_limitation=substantive_cost_limitation
            ),
        },
        **overrides,
    )


def build_claim(**overrides) -> Claim:
    """Final bill by default; use the presets for other coherent field sets."""
    defaults = {
        "claim_reference": next_claim_reference(),
        "claim_type_id": ClaimType.FINAL_BILL,
        "status_id": ClaimStatus.SUBMITTED,
        "submission_date": DEFAULT_SUBMISSION_DATE,
        "claimant_id": "claimant-123@provider.co.uk",
        "total_profit_cost_net": Decimal("100.00"),
        "total_profit_cost_gross": Decimal("120.00"),
        "total_profit_cost_vat_zero": Decimal("0.00"),
    }
    return Claim(**(defaults | overrides))


def build_poa_claim(**overrides) -> Claim:
    return build_claim(
        **(
            {
                "claim_type_id": ClaimType.PAYMENT_ON_ACCOUNT,
                "poa_type_id": POAType.PROFIT_COST,
                "total_profit_cost_net": Decimal("1000.00"),
                "total_profit_cost_gross": Decimal("1200.00"),
                "total_profit_cost_vat_zero": Decimal("500.00"),
            }
            | overrides
        )
    )


def build_nil_bill_claim(**overrides) -> Claim:
    return build_claim(
        **(
            {
                "claim_type_id": ClaimType.NIL_BILL,
                "total_profit_cost_net": None,
                "total_profit_cost_gross": Decimal("0.00"),
                "total_profit_cost_vat_zero": None,
            }
            | overrides
        )
    )


def build_claim_evidence(**overrides) -> ClaimEvidence:
    defaults = {"sds_file_name": "evidence_abc123.pdf", "file_name": "evidence.pdf"}
    return ClaimEvidence(**(defaults | overrides))


def build_claim_decision(**overrides) -> ClaimDecision:
    defaults = {"decision": ClaimDecisionStatus.REJECT}
    return ClaimDecision(**(defaults | overrides))


def build_decision_reason(**overrides) -> DecisionReason:
    defaults = {
        "reason_code": ReasonCode.MAX_POA_CLAIMS_EXCEEDED,
        "justification": "Too many payment on account claims",
    }
    return DecisionReason(**(defaults | overrides))


def build_claim_inquest_outcome(**overrides) -> ClaimInquestOutcome:
    defaults = {"inquest_outcome_id": InquestOutcomeCode.NATURAL_CAUSES}
    return ClaimInquestOutcome(**(defaults | overrides))


def build_claim_cost_template(**overrides) -> ClaimCostTemplate:
    defaults = {
        "claim_cost_template_file_id": uuid.uuid4(),
        "claim_cost_template_file_name": "cost_template.xlsx",
    }
    return ClaimCostTemplate(**(defaults | overrides))


def build_claim_payment_extract(**overrides) -> ClaimPaymentExtract:
    sequence_number = overrides.get("sequence_number", 1)
    defaults = {
        "sequence_number": sequence_number,
        "invoice_number": f"INV-{uuid.uuid4().hex[:8].upper()}",
        "invoice_amount": Decimal("100.00"),
        "invoice_date": date(2026, 1, 1),
        "invoice_type": InvoiceTypeCode.POA,
        "tax_code": TaxCode.ZERO_VAT,
    }
    return ClaimPaymentExtract(**(defaults | overrides))


# --- History ---------------------------------------------------------------


def build_history_event(**overrides) -> HistoryEvent:
    defaults = {
        "event_reference": HistoryEventReference.CASE_NOTE_ADDED,
        "actor": "actor",
        "actor_type": ActorType.PROVIDER,
        "event_data": None,
    }
    return HistoryEvent(**(defaults | overrides))


# --- Certificate -----------------------------------------------------------


def build_certificate(
    application=UNSET,
    application_proceeding=UNSET,
    public_bodies=UNSET,
    **overrides,
) -> ApplicationCertificate:
    if application is UNSET:
        application = build_application()
    if application_proceeding is UNSET:
        application_proceeding = build_application_proceeding()
    if public_bodies is UNSET:
        public_bodies = [build_application_public_body()]

    client_address = (
        application.client.correspondence_address or application.client.home_address
    )
    defaults = {
        "client_name": f"{application.client.client_first_name} {application.client.client_last_name}",
        "client_address": client_address,
        "firm_name": application.provider.firm_code,
        "office_address": build_office_address(),
        "opponent_details": [body.public_body_description for body in public_bodies],
        "guardian_name": "Not applicable",
        "guardian_address": "Not applicable",
        "laa_reference": application.laa_reference,
        "date_created": application_proceeding.certificate_issue_date
        or datetime.now(tz=UTC).date(),
        "certificate_type": application_proceeding.proceeding.certificate_type,
        "status": application.status,
        "effective_date": application_proceeding.certificate_start_date
        or datetime.now(tz=UTC).date(),
        "end_date": None,
        "reinstatement_date": None,
        "cost_limitation": str(
            application_proceeding.proceeding.substantive_cost_limitation
        ),
        "cost_limitation_effective_date": application_proceeding.substantive_cost_limitation_effective_date
        or datetime.now(tz=UTC).date(),
        "certificate_limitation": "Not applicable",
        "proceeding_name": application_proceeding.proceeding.proceeding_name,
        "proceeding_description": application_proceeding.proceeding.proceeding_description,
        "category_of_law": application_proceeding.proceeding.category_of_law,
        "current_proceeding_status": application.status,
        "date_work_can_commence": application_proceeding.certificate_start_date
        or datetime.now(tz=UTC).date(),
        "proceeding_end_date": None,
        "client_involvement_type": "Applicant",
        "level_of_service": application_proceeding.proceeding.level_of_service,
        "date_current_level_of_service_effective": (
            application_proceeding.certificate_start_date or datetime.now(tz=UTC).date()
        ),
        "previous_level_of_service": "Not applicable",
        "date_previous_level_of_service_effective": "Not applicable",
        "scope_limitation_heading": application_proceeding.proceeding.scope_limitation_heading,
        "scope_limitation_description": application_proceeding.proceeding.scope_description,
    }
    return ApplicationCertificate(**(defaults | overrides))
