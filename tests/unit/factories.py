from datetime import date

from app.models.application.index import (
    Address,
    Application,
    ApplicationProceeding,
    ApplicationPublicBody,
    Client,
    Deceased,
    Proceeding,
    ProceedingId,
    Provider,
    PublicBody,
    PublicBodyId,
)
from app.models.application.enums import AddressSource, CorrespondenceRecipientType


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


def create_base_client(
    home_address=_NOT_PROVIDED, correspondence_address=_NOT_PROVIDED, **overrides
):
    """Create a base client with optional field overrides."""
    if home_address is _NOT_PROVIDED:
        home_address = create_base_home_address()

    if correspondence_address is _NOT_PROVIDED:
        correspondence_address = create_base_correspondence_address()

    defaults = {
        "client_id": 1,
        "client_first_name": "Jane",
        "client_last_name": "Doe",
        "client_last_name_at_birth": "Smith",
        "date_of_birth": "15-06-1985",
        "national_insurance_number": "AB123456C",
        "has_applied_previously": True,
        "prev_application_reference": "LAA-2024-001",
        "correspondence_address_source": AddressSource.USE_SPECIFIED_ADDRESS,
        "home_address_id": 1,
        "home_address": home_address,
        "correspondence_address_id": 2,
        "correspondence_address": correspondence_address,
        "is_client_correspondence_recipient": False,
        "correspondence_recipient_type": CorrespondenceRecipientType.PERSON,
        "correspondence_recipient_name": "John Smith",
    }
    return Client(**(defaults | overrides))


def create_base_deceased(**overrides):
    """Create a base deceased with optional field overrides."""
    defaults = {
        "deceased_id": 1,
        "client_id": 1,
        "deceased_first_name": "Robert",
        "deceased_last_name": "Johnson",
        "deceased_date_of_birth": "01-01-1950",
        "deceased_date_of_death": "31-12-2025",
        "coroners_reference": "COR-2025-123",
        "further_information": "Additional context",
        "client_relationship_to_deceased": "Son",
    }
    return Deceased(**(defaults | overrides))


def create_base_proceeding(**overrides):
    """Create a base proceeding with optional field overrides."""
    defaults = {
        "id": 1,
        "proceeding_id": ProceedingId.TEST1,
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
        "laa_reference": 12345,
        "proceeding_id": ProceedingId.TEST1,
        "proceeding": proceeding,
        "certificate_start_date": date(2026, 6, 18),
        "certificate_issue_date": date(2026, 6, 18),
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
        "laa_reference": 12345,
        "public_body_id": PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
        "public_body": public_body,
    }
    return ApplicationPublicBody(**(defaults | overrides))


def create_base_provider(**overrides):
    """Create a base provider with optional field overrides."""
    defaults = {
        "provider_id": 1,
        "firm_code": "ABC123",
        "office_id": "001",
    }
    return Provider(**(defaults | overrides))


def create_base_application(
    client=_NOT_PROVIDED,
    deceased=_NOT_PROVIDED,
    provider=_NOT_PROVIDED,
    proceedings=_NOT_PROVIDED,
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
    if proceedings is _NOT_PROVIDED:
        proceedings = [create_base_application_proceeding()]
    if public_bodies is _NOT_PROVIDED:
        public_bodies = [create_base_application_public_body()]

    defaults = {
        "laa_reference": 12345,
        "client_id": 1,
        "client": client,
        "deceased_id": 1,
        "deceased": deceased,
        "provider_id": 1,
        "provider": provider,
        "proceedings": proceedings,
        "public_bodies": public_bodies,
    }
    return Application(**(defaults | overrides))
