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
from app.use_cases.notify.create_application_submission_email_personalisation import (
    create_application_submission_email_personalisation,
)
from app.models.gov_notify_templates.application_submit_personalisation import (
    NotifyApplicationSubmitTemplatePersonalisation,
)

import pytest


# Sentinel value to distinguish "not provided" from "explicitly None"
_NOT_PROVIDED = object()


# Factory functions to reduce code duplication


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


def test_create_application_submission_email_personalisation_returns_all_required_fields():
    """
    Test that create_application_submission_email_personalisation returns all fields required by the GovNotify template.
    """
    application = create_base_application()

    result = create_application_submission_email_personalisation(application)

    assert isinstance(result, NotifyApplicationSubmitTemplatePersonalisation)

    assert result.laa_reference == "12345"
    assert result.client_first_name == "Jane"
    assert result.client_last_name == "Doe"
    assert result.client_last_name_at_birth == "Smith"
    assert result.date_of_birth == "15-06-1985"
    assert result.national_insurance_number == "AB123456C"
    assert result.has_applied_previously == "Yes"
    assert result.prev_application_reference == "LAA-2024-001"
    assert "123 Main St" in result.client_home_address
    assert "Apt 4B" in result.client_home_address
    assert "London" in result.client_home_address
    assert "SW1A 1AA" in result.client_home_address
    assert "456 Oak Ave" in result.correspondence_address
    assert "Manchester" in result.correspondence_address
    assert "M1 1AA" in result.correspondence_address
    assert result.correspondence_recipient == "John Smith (PERSON)"
    assert result.client_relationship_to_deceased == "Son"
    assert result.proceeding_description == "Inquest into death"
    assert result.matter_type == "INQUESTS"
    assert result.deceased_first_name == "Robert"
    assert result.deceased_last_name == "Johnson"
    assert result.deceased_date_of_birth == "01-01-1950"
    assert result.deceased_date_of_death == "31-12-2025"
    assert result.deceased_related_applications_information == "Additional context"
    assert result.deceased_has_other_related_applications == "Yes"
    assert result.coroners_reference == "COR-2025-123"
    assert result.public_body_description == "Department for Transport"
    assert result.file_name == "N/A"


def test_application_submit_email_personalisation_rejects_missing_required_fields():
    """
    Test that NotifyApplicationSubmitTemplatePersonalisation model rejects creation with missing required fields.
    """
    with pytest.raises(Exception):
        NotifyApplicationSubmitTemplatePersonalisation(
            laa_reference="12345",
            client_first_name="Test",
        )


def test_application_submit_email_personalisation_rejects_extra_fields():
    """
    Test that NotifyApplicationSubmitTemplatePersonalisation model rejects extra/unexpected fields.
    """
    with pytest.raises(Exception):
        NotifyApplicationSubmitTemplatePersonalisation(
            laa_reference="12345",
            client_first_name="Test",
            client_last_name="User",
            date_of_birth="01-01-1990",
            has_applied_previously="No",
            client_home_address="Test Address",
            correspondence_address="Test Address",
            correspondence_recipient="Client",
            client_relationship_to_deceased="Son",
            proceeding_description="Test Proceeding",
            matter_type="INQUESTS",
            deceased_first_name="Test",
            deceased_last_name="Deceased",
            deceased_date_of_birth="01-01-1950",
            deceased_date_of_death="01-01-2025",
            coroners_reference="COR-123",
            public_body_description="Test Department",
            unexpected_field="This should not be allowed",
        )


def test_create_application_submission_email_personalisation_handles_optional_fields():
    """
    Test that create_application_submission_email_personalisation handles missing/optional fields correctly.
    """
    client = create_base_client(
        client_last_name_at_birth=None,
        national_insurance_number=None,
        has_applied_previously=False,
        prev_application_reference=None,
        correspondence_address_source=AddressSource.USE_CLIENT_HOME_ADDRESS,
        correspondence_address=None,
        is_client_correspondence_recipient=True,
        correspondence_recipient_type=None,
        correspondence_recipient_name=None,
    )

    deceased = create_base_deceased(
        further_information=None,
    )

    application = create_base_application(
        client=client,
        deceased=deceased,
    )

    result = create_application_submission_email_personalisation(application)

    assert isinstance(result, NotifyApplicationSubmitTemplatePersonalisation)
    assert result.client_last_name_at_birth == "Not provided"
    assert result.national_insurance_number == "Not provided"
    assert result.has_applied_previously == "No"
    assert result.prev_application_reference == "Not provided"
    assert result.correspondence_address == "Same as home address"
    assert result.correspondence_recipient == "Client"
    assert result.deceased_related_applications_information == ""
    assert result.deceased_has_other_related_applications == "No"


def test_create_application_submission_email_personalisation_formats_address_correctly():
    """
    Test that addresses are formatted correctly with line breaks.
    """
    home_address = create_base_home_address(
        address_line_1="123 Test Street",
        address_line_2="Floor 2",
        town_or_city="Test City",
        county="Test County",
        postcode="TC1 1TC",
    )

    client = create_base_client(
        home_address=home_address,
    )

    application = create_base_application(
        client=client,
    )

    result = create_application_submission_email_personalisation(application)

    assert isinstance(result, NotifyApplicationSubmitTemplatePersonalisation)
    expected_address = "123 Test Street\nFloor 2\nTest City\nTest County\nTC1 1TC"
    assert result.client_home_address == expected_address


def test_default_home_address_value_set_to_no_fixed_abode_when_not_provided():
    """
    Test that default value for home address is set correctly.
    """
    client = create_base_client(
        home_address=None,
    )

    application = create_base_application(client=client)

    result = create_application_submission_email_personalisation(application)

    assert isinstance(result, NotifyApplicationSubmitTemplatePersonalisation)

    assert result.client_home_address == "No fixed abode"
    assert "456 Oak Ave" in result.correspondence_address
    assert "Manchester" in result.correspondence_address
    assert "M1 1AA" in result.correspondence_address
