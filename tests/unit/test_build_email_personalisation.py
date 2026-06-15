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
from app.use_cases.build_email_personalisation import build_email_personalisation
from app.models.notifications.personalisation import EmailPersonalisation
from app.config import Config


def test_build_email_personalisation_returns_all_required_fields():
    """
    Test that build_email_personalisation returns all fields required by the GovNotify template.
    """
    # Arrange - create test application with all related data
    home_address = Address(
        address_id=1,
        address_line_1="123 Main St",
        address_line_2="Apt 4B",
        town_or_city="London",
        county="Greater London",
        postcode="SW1A 1AA",
    )

    correspondence_address = Address(
        address_id=2,
        address_line_1="456 Oak Ave",
        town_or_city="Manchester",
        county="Greater Manchester",
        postcode="M1 1AA",
    )

    client = Client(
        client_id=1,
        client_first_name="Jane",
        client_last_name="Doe",
        client_last_name_at_birth="Smith",
        date_of_birth="15-06-1985",
        national_insurance_number="AB123456C",
        has_applied_previously=True,
        prev_application_reference="LAA-2024-001",
        correspondence_address_source=AddressSource.USE_SPECIFIED_ADDRESS,
        home_address_id=1,
        home_address=home_address,
        correspondence_address_id=2,
        correspondence_address=correspondence_address,
        is_client_correspondence_recipient=False,
        correspondence_recipient_type=CorrespondenceRecipientType.PERSON,
        correspondence_recipient_name="John Smith",
    )

    deceased = Deceased(
        deceased_id=1,
        client_id=1,
        deceased_first_name="Robert",
        deceased_last_name="Johnson",
        deceased_date_of_birth="01-01-1950",
        deceased_date_of_death="31-12-2025",
        coroners_reference="COR-2025-123",
        further_information="Additional context",
        client_relationship_to_deceased="Son",
    )

    proceeding = Proceeding(
        id=1,
        proceeding_id=ProceedingId.TEST1,
        proceeding_description="Inquest into death",
        matter_type="INQUESTS",
    )

    application_proceeding = ApplicationProceeding(
        application_proceeding_id=1,
        laa_reference=12345,
        proceeding_id=ProceedingId.TEST1,
        proceeding=proceeding,
    )

    public_body = PublicBody(
        id=1,
        public_body_id=PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
        public_body_description="Department for Transport",
    )

    application_public_body = ApplicationPublicBody(
        application_public_body_id=1,
        laa_reference=12345,
        public_body_id=PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
        public_body=public_body,
    )

    provider = Provider(
        provider_id=1,
        firm_code="ABC123",
        office_id="001",
    )

    application = Application(
        laa_reference=12345,
        client_id=1,
        client=client,
        deceased_id=1,
        deceased=deceased,
        provider_id=1,
        provider=provider,
        proceedings=[application_proceeding],
        public_bodies=[application_public_body],
    )

    # Act
    result = build_email_personalisation(application)

    # Assert - verify result is EmailPersonalisation model
    assert isinstance(result, EmailPersonalisation)

    # Assert - verify all template fields are present and correct
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
    assert result.coroners_reference == "COR-2025-123"
    assert result.public_body_description == "Department for Transport"
    assert result.file_name == "N/A"
    assert result.feedback_link == Config.FEEDBACK_LINK


def test_build_email_personalisation_handles_optional_fields():
    """
    Test that build_email_personalisation handles missing/optional fields correctly.
    """
    # Arrange - minimal application data
    home_address = Address(
        address_id=1,
        address_line_1="1 Test Lane",
        town_or_city="Testville",
        postcode="T1 1TT",
    )

    client = Client(
        client_id=1,
        client_first_name="John",
        client_last_name="Test",
        date_of_birth="01-01-1990",
        correspondence_address_source=AddressSource.USE_CLIENT_HOME_ADDRESS,
        home_address_id=1,
        home_address=home_address,
        is_client_correspondence_recipient=True,
    )

    deceased = Deceased(
        deceased_id=1,
        client_id=1,
        deceased_first_name="Test",
        deceased_last_name="Person",
        deceased_date_of_birth="01-01-1960",
        deceased_date_of_death="01-01-2025",
        coroners_reference="COR-2025-999",
        further_information=None,
        client_relationship_to_deceased="Friend",
    )

    proceeding = Proceeding(
        id=1,
        proceeding_id=ProceedingId.TEST1,
        proceeding_description="Test proceeding",
        matter_type="INQUESTS",
    )

    application_proceeding = ApplicationProceeding(
        application_proceeding_id=1,
        laa_reference=99999,
        proceeding_id=ProceedingId.TEST1,
        proceeding=proceeding,
    )

    public_body = PublicBody(
        id=1,
        public_body_id=PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
        public_body_description="Test Department",
    )

    application_public_body = ApplicationPublicBody(
        application_public_body_id=1,
        laa_reference=99999,
        public_body_id=PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
        public_body=public_body,
    )

    provider = Provider(provider_id=1, firm_code="TEST", office_id="999")

    application = Application(
        laa_reference=99999,
        client_id=1,
        client=client,
        deceased_id=1,
        deceased=deceased,
        provider_id=1,
        provider=provider,
        proceedings=[application_proceeding],
        public_bodies=[application_public_body],
    )

    # Act
    result = build_email_personalisation(application)

    # Assert - verify optional fields are handled
    assert isinstance(result, EmailPersonalisation)
    assert result.client_last_name_at_birth == "N/A"
    assert result.national_insurance_number == "N/A"
    assert result.has_applied_previously == "No"
    assert result.prev_application_reference == "N/A"
    assert result.correspondence_address == "Same as home address"
    assert result.correspondence_recipient == "Client"


def test_build_email_personalisation_formats_address_correctly():
    """
    Test that addresses are formatted correctly with line breaks.
    """
    # Arrange
    home_address = Address(
        address_id=1,
        address_line_1="123 Test Street",
        address_line_2="Floor 2",
        town_or_city="Test City",
        county="Test County",
        postcode="TC1 1TC",
    )

    client = Client(
        client_id=1,
        client_first_name="Test",
        client_last_name="User",
        date_of_birth="01-01-1990",
        correspondence_address_source=AddressSource.USE_CLIENT_HOME_ADDRESS,
        home_address_id=1,
        home_address=home_address,
        is_client_correspondence_recipient=True,
    )

    deceased = Deceased(
        deceased_id=1,
        client_id=1,
        deceased_first_name="Test",
        deceased_last_name="Deceased",
        deceased_date_of_birth="01-01-1950",
        deceased_date_of_death="01-01-2025",
        coroners_reference="COR-123",
        further_information=None,
        client_relationship_to_deceased="Relative",
    )

    proceeding = Proceeding(
        id=1,
        proceeding_id=ProceedingId.TEST1,
        proceeding_description="Test",
        matter_type="INQUESTS",
    )

    application_proceeding = ApplicationProceeding(
        application_proceeding_id=1,
        laa_reference=11111,
        proceeding_id=ProceedingId.TEST1,
        proceeding=proceeding,
    )

    public_body = PublicBody(
        id=1,
        public_body_id=PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
        public_body_description="Test",
    )

    application_public_body = ApplicationPublicBody(
        application_public_body_id=1,
        laa_reference=11111,
        public_body_id=PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
        public_body=public_body,
    )

    provider = Provider(provider_id=1, firm_code="TEST", office_id="001")

    application = Application(
        laa_reference=11111,
        client_id=1,
        client=client,
        deceased_id=1,
        deceased=deceased,
        provider_id=1,
        provider=provider,
        proceedings=[application_proceeding],
        public_bodies=[application_public_body],
    )

    # Act
    result = build_email_personalisation(application)

    # Assert - address should be formatted with line breaks
    assert isinstance(result, EmailPersonalisation)
    expected_address = "123 Test Street\nFloor 2\nTest City\nTest County\nTC1 1TC"
    assert result.client_home_address == expected_address
