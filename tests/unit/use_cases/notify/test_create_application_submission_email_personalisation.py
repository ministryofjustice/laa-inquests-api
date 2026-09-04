import pytest
from pydantic import ValidationError

from app.models.application.enums import AddressSource
from app.models.gov_notify_templates.application_submit_personalisation import (
    NotifyApplicationSubmitTemplatePersonalisation,
)
from app.use_cases.notify.create_application_submission_email_personalisation import (
    create_application_submission_email_personalisation,
)
from tests.unit.factories import (
    create_base_application,
    create_base_client,
    create_base_deceased,
    create_base_home_address,
)


def test_create_application_submission_email_personalisation_returns_all_required_fields():
    """
    Test that create_application_submission_email_personalisation returns all fields required by the GovNotify template.
    """
    application = create_base_application()

    result = create_application_submission_email_personalisation(application)

    assert isinstance(result, NotifyApplicationSubmitTemplatePersonalisation)

    assert result.laa_reference == "INQ-YYY-YYY"
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
    assert result.correspondence_recipient == "Client"
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
    with pytest.raises(ValidationError):
        NotifyApplicationSubmitTemplatePersonalisation(
            laa_reference="12345",
            client_first_name="Test",
        )


def test_application_submit_email_personalisation_rejects_extra_fields():
    """
    Test that NotifyApplicationSubmitTemplatePersonalisation model rejects extra/unexpected fields.
    """
    with pytest.raises(ValidationError):
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
