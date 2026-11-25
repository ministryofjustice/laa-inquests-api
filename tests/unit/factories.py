import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.application_backlog_report import ApplicationBacklogRecord
from app.domain.claim import Claim as ClaimDomain
from app.domain.claim_evidence import ClaimEvidence as ClaimEvidenceDomain
from app.domain.coroners_letter import CoronersLetter as CoronersLetterDomain
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
    ClaimStatus,
    ClaimType,
    InquestOutcomeCode,
    NumberOfCounselInstructed,
    POAType,
)
from app.models.claim.index import Claim, ClaimEvidence

# Sentinel value to distinguish "not provided" from "explicitly None"
_NOT_PROVIDED = object()


def create_base_home_address(**overrides):
    """Create a base home address with optional field overrides."""
    defaults = {
        "address_id": 1,
        "address_line_1": "123 Main St",
        "address_line_2": "Apt 4B",
        "town_or_city": "London",
        "county": "Greater London",
        "postcode": "SW1A 1AA",
    }
    return Address(**(defaults | overrides))


def create_base_correspondence_address(**overrides):
    """Create a base correspondence address with optional field overrides."""
    defaults = {
        "address_id": 2,
        "address_line_1": "456 Oak Ave",
        "town_or_city": "Manchester",
        "county": "Greater Manchester",
        "postcode": "M1 1AA",
    }
    return Address(**(defaults | overrides))


def create_base_office_address(**overrides):
    """Create a base office address with optional field overrides."""
    defaults = {
        "address_id": 3,
        "address_line_1": "123 Main St",
        "address_line_2": "Apt 4B",
        "town_or_city": "London",
        "county": "Greater London",
        "postcode": "SW1A 1AA",
    }
    return Address(**(defaults | overrides))


def create_base_client(
    home_address=_NOT_PROVIDED,
    correspondence_address=_NOT_PROVIDED,
    correspondence_recipient_name=_NOT_PROVIDED,
    correspondence_recipient_type=_NOT_PROVIDED,
    **overrides,
):
    """Create a base client with optional field overrides."""
    if home_address is _NOT_PROVIDED:
        home_address = create_base_home_address()

    if correspondence_address is _NOT_PROVIDED:
        correspondence_address = create_base_correspondence_address()

    if (
        correspondence_recipient_name is _NOT_PROVIDED
        and correspondence_recipient_type is _NOT_PROVIDED
    ):
        correspondence_recipient_name = None
        correspondence_recipient_type = None
    elif (
        correspondence_recipient_name is not _NOT_PROVIDED
        and correspondence_recipient_type is _NOT_PROVIDED
    ):
        correspondence_recipient_type = CorrespondenceRecipientType.PERSON
    elif (
        correspondence_recipient_name is _NOT_PROVIDED
        and correspondence_recipient_type is not _NOT_PROVIDED
    ):
        correspondence_recipient_name = "Recipient Name"

    defaults = {
        "client_id": 1,
        "client_first_name": "Jane",
        "client_last_name": "Doe",
        "client_last_name_at_birth": "Smith",
        "date_of_birth": "15-06-1985",
        "national_insurance_number": "AB123456C",
        "has_applied_previously": True,
        "prev_application_reference": "LAA-2024-001",
        "correspondence_address_source": AddressSource.USE_CLIENT_HOME_ADDRESS,
        "home_address_id": 1,
        "home_address": home_address,
        "correspondence_address_id": 2,
        "correspondence_address": correspondence_address,
        "correspondence_recipient_type": correspondence_recipient_type,
        "correspondence_recipient_name": correspondence_recipient_name,
    }
    return Client(**(defaults | overrides))


def create_base_deceased(**overrides):
    """Create a base deceased with optional field overrides."""
    defaults = {
        "deceased_id": 1,
        "client_id": 1,
        "deceased_first_name": "Robert",
        "deceased_last_name": "Johnson",
        "deceased_date_of_birth": "1950-01-01",
        "deceased_date_of_death": "2025-12-31",
        "coroners_reference": "COR-2025-123",
        "further_information": "Additional context",
        "client_relationship_to_deceased": "Son",
    }
    return Deceased(**(defaults | overrides))


def create_base_proceeding(**overrides):
    """Create a base proceeding with optional field overrides."""
    defaults = {
        "id": 1,
        "proceeding_id": ProceedingId.IQ042,
        "proceeding_name": "Inquest into death",
        "proceeding_description": "Inquest into death",
        "matter_type": "INQUESTS",
    }
    return Proceeding(**(defaults | overrides))


def create_base_application_proceeding(proceeding=_NOT_PROVIDED, **overrides):
    """Create a base application proceeding with optional field overrides."""
    if proceeding is _NOT_PROVIDED:
        proceeding = create_base_proceeding()

    defaults = {
        "application_proceeding_id": 1,
        "application_id": 12345,
        "proceeding_id": ProceedingId.IQ042,
        "proceeding": proceeding,
        "certificate_start_date": datetime(2026, 6, 18, tzinfo=UTC),
        "certificate_issue_date": datetime(2026, 6, 18, tzinfo=UTC),
        "substantive_cost_limitation_effective_date": datetime(2026, 6, 18, tzinfo=UTC),
        "certificate_end_date": None,
    }
    return ApplicationProceeding(**(defaults | overrides))


def create_base_public_body(**overrides):
    """Create a base public body with optional field overrides."""
    defaults = {
        "id": 1,
        "public_body_id": PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
        "public_body_description": "Department for Transport",
    }
    return PublicBody(**(defaults | overrides))


def create_base_application_public_body(public_body=_NOT_PROVIDED, **overrides):
    """Create a base application public body with optional field overrides."""
    if public_body is _NOT_PROVIDED:
        public_body = create_base_public_body()

    defaults = {
        "application_public_body_id": 1,
        "application_id": 12345,
        "public_body_id": PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
        "public_body": public_body,
    }
    return ApplicationPublicBody(**(defaults | overrides))


def create_base_provider(**overrides):
    """Create a base provider with optional field overrides."""
    defaults = {
        "provider_id": 1,
        "firm_code": "ABC123",
        "office_id": "0U651L",
        "email_address": "provider@example.com",
    }
    return Provider(**(defaults | overrides))


def create_base_application(
    client=_NOT_PROVIDED,
    deceased=_NOT_PROVIDED,
    provider=_NOT_PROVIDED,
    proceeding=_NOT_PROVIDED,
    public_bodies=_NOT_PROVIDED,
    **overrides,
):
    """Create a base application with optional field overrides."""
    if client is _NOT_PROVIDED:
        client = create_base_client()
    if deceased is _NOT_PROVIDED:
        deceased = create_base_deceased()
    if provider is _NOT_PROVIDED:
        provider = create_base_provider()
    if proceeding is _NOT_PROVIDED:
        proceeding = create_base_application_proceeding()
    if public_bodies is _NOT_PROVIDED:
        public_bodies = [create_base_application_public_body()]

    defaults = {
        "application_id": 12345,
        "laa_reference": "INQ-YYY-YYY",
        "client_id": 1,
        "client": client,
        "deceased_id": 1,
        "deceased": deceased,
        "provider_id": 1,
        "provider": provider,
        "proceeding": proceeding,
        "public_bodies": public_bodies,
    }
    return Application(**(defaults | overrides))


def create_base_claim(**overrides) -> Claim:
    """Create a base claim with optional field overrides."""
    defaults = {
        "claim_type_id": "FINAL_BILL",
        "status_id": ClaimStatus.SUBMITTED,
        "submission_date": datetime(2026, 1, 1, tzinfo=UTC),
    }
    return Claim(**(defaults | overrides))


def create_base_poa_claim(**overrides) -> Claim:
    """Create a base payment-on-account claim with standard POA amounts."""
    defaults = {
        "claim_id": 1,
        "application_id": 1,
        "claim_reference": "INQC-0000-0001",
        "claim_type_id": ClaimType.PAYMENT_ON_ACCOUNT,
        "total_profit_cost_net": Decimal("1000.00"),
        "total_profit_cost_gross": Decimal("1200.00"),
        "total_profit_cost_vat_zero": Decimal("500.00"),
        "poa_type_id": POAType.PROFIT_COST,
    }
    return create_base_claim(**(defaults | overrides))


def create_base_claim_domain(**overrides) -> ClaimDomain:
    """Create a base payment-on-account claim domain object with optional field overrides."""
    defaults = {
        "claim_type": ClaimType.PAYMENT_ON_ACCOUNT,
        "net": Decimal("1000.00"),
        "gross": Decimal("1200.00"),
        "vat_zero_total": None,
        "poa_type": POAType.PROFIT_COST,
    }
    return ClaimDomain(**(defaults | overrides))


def create_base_final_bill_claim_domain(**overrides) -> ClaimDomain:
    """Create a base final-bill claim domain object with optional field overrides."""
    defaults = {
        "claim_type": ClaimType.FINAL_BILL,
        "poa_type": None,
        "inquest_outcomes": (InquestOutcomeCode.NATURAL_CAUSES,),
        "cost_template_file_id": uuid.uuid4(),
        "cost_template_file_name": "costs.xlsx",
        "has_counsel_been_paid": True,
        "has_alternative_funding": False,
        "has_recovery_costs_awarded": True,
        "financial_recovery_previous_pre_certificate_costs": Decimal("100.00"),
        "financial_recovery_cost": Decimal("200.00"),
        "financial_recovery_damages": Decimal("300.00"),
        "financial_recovery_interest": Decimal("50.00"),
        "paying_party": "Test Council",
        "number_of_counsel_instructed": NumberOfCounselInstructed.TWO,
    }
    return create_base_claim_domain(**(defaults | overrides))


def create_base_certificate(
    application=_NOT_PROVIDED,
    application_proceeding=_NOT_PROVIDED,
    public_bodies=_NOT_PROVIDED,
    **overrides,
):
    """Create a base certificate with optional field overrides."""
    if application is _NOT_PROVIDED:
        application = create_base_application()
    if application_proceeding is _NOT_PROVIDED:
        application_proceeding = create_base_application_proceeding()
    if public_bodies is _NOT_PROVIDED:
        public_bodies = [create_base_application_public_body()]

    client_address = (
        application.client.correspondence_address or application.client.home_address
    )
    defaults = {
        "client_name": f"{application.client.client_first_name} {application.client.client_last_name}",
        "client_address": client_address,
        "firm_name": application.provider.firm_code,
        "office_address": create_base_office_address(),
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


def create_base_application_backlog_record(**overrides):
    defaults = {
        "laa_reference": "INQ-AAA-001",
        "merits_decision": MeritsDecision.SUBMITTED,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "firm_code": "123",
        "office_id": "T3STID",
        "proceeding_description": "Inquest",
        "matter_type": "INQUESTS",
        "potential_duplicate_applications": [],
    }
    return ApplicationBacklogRecord(**(defaults | overrides))


def create_base_coroners_letter(**overrides) -> CoronersLetter:
    """Create a base coroner's letter database model with optional field overrides."""
    defaults = {
        "sds_file_name": "coroners-letter_abc123.pdf",
        "file_name": "test-coroners-letter.pdf",
        "office_id": "0U651L",
    }
    return CoronersLetter(**(defaults | overrides))


def create_base_coroners_letter_domain(**overrides) -> CoronersLetterDomain:
    """Create a base coroner's letter domain object with optional field overrides."""
    defaults = {
        "sds_file_name": "coroners-letter_abc123.pdf",
        "file_name": "test-coroners-letter.pdf",
        "office_id": "0U651L",
    }
    return CoronersLetterDomain(**(defaults | overrides))


def create_base_claim_evidence(**overrides) -> ClaimEvidence:
    """Create a base claim evidence database model with optional field overrides."""
    defaults = {
        "sds_file_name": "claim-evidence_abc123.pdf",
        "file_name": "test-claim-evidence.pdf",
        "office_id": "0U651L",
    }
    return ClaimEvidence(**(defaults | overrides))


def create_base_claim_evidence_domain(**overrides) -> ClaimEvidenceDomain:
    """Create a base claim evidence domain object with optional field overrides."""
    defaults = {
        "sds_file_name": "claim-evidence_abc123.pdf",
        "file_name": "test-claim-evidence.pdf",
        "office_id": "0U651L",
    }
    return ClaimEvidenceDomain(**(defaults | overrides))
