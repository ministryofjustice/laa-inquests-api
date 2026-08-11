"""Tests for the CreateCertificateModel use case"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.models.application.certificate import ApplicationCertificate
from app.models.application.enums import MeritsDecision
from app.use_cases.create_certificate_context import CreateCertificateContextUseCase
from app.use_cases.exceptions import ProviderDetailsRetrievalError
from tests.unit.factories import (
    create_base_application,
    create_base_application_proceeding,
    create_base_application_public_body,
    create_base_client,
    create_base_correspondence_address,
    create_base_home_address,
    create_base_office_address,
    create_base_proceeding,
    create_base_provider,
    create_base_public_body,
)


def test_populate_certificate_context_returns_ApplicationCertificate():
    """Test that populate_certificate_context returns an ApplicationCertificate."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Test Firm Ltd"
    mock_provider_port.get_office_address.return_value = create_base_office_address()
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    # Use factory defaults - they already include all required fields
    application = create_base_application()

    result = usecase.populate_certificate_context(application, application.proceeding)

    assert isinstance(result, ApplicationCertificate)


def test_populate_certificate_context_populates_client_fields_correctly():
    """Test that client name and address are populated correctly."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Smith & Associates"
    mock_provider_port.get_office_address.return_value = create_base_office_address()
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    # Override only the specific fields we're testing
    home_address = create_base_home_address(
        address_line_1="10 Downing Street",
        address_line_2="Westminster",
        postcode="SW1A 2AA",
    )
    client = create_base_client(
        client_first_name="John",
        client_last_name="Smith",
        home_address=home_address,
        correspondence_address=None,
    )
    application = create_base_application(client=client)

    result = usecase.populate_certificate_context(application, application.proceeding)

    assert result.client_name == "John Smith"
    assert result.client_address is not None
    assert result.client_address.address_line_1 == "10 Downing Street"
    assert result.client_address.address_line_2 == "Westminster"
    assert result.client_address.postcode == "SW1A 2AA"


def test_populate_certificate_context_uses_correspondence_address_and_care_of_recipient_when_available():
    """Test that correspondence address is used when available."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Test Firm"
    mock_provider_port.get_office_address.return_value = create_base_office_address()
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    # Only override the specific address fields we're testing
    correspondence_address = create_base_correspondence_address(
        address_line_1="456 Oak Avenue",
        town_or_city="Manchester",
        postcode="M1 2AB",
    )
    client = create_base_client(
        correspondence_address_source="USE_SPECIFIED_ADDRESS",
        correspondence_address=correspondence_address,
        is_client_correspondence_recipient=False,
    )
    application = create_base_application(client=client)

    result = usecase.populate_certificate_context(application, application.proceeding)

    assert result.client_address is not None
    assert result.client_address.address_line_1 == "c/o John Smith 456 Oak Avenue"
    assert result.client_address.town_or_city == "Manchester"
    assert result.client_address.postcode == "M1 2AB"


def test_populate_certificate_context_does_not_use_care_of_recipient_name_when_client_is_correspondence_recipient():
    """Test that correspondence address is not used when client is the correspondence recipient."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Test Firm"
    mock_provider_port.get_office_address.return_value = create_base_office_address()
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    # Only override the specific address fields we're testing
    correspondence_address = create_base_correspondence_address(
        address_line_1="456 Oak Avenue",
        town_or_city="Manchester",
        postcode="M1 2AB",
    )
    client = create_base_client(
        correspondence_address_source="USE_SPECIFIED_ADDRESS",
        correspondence_address=correspondence_address,
        is_client_correspondence_recipient=True,
    )
    application = create_base_application(client=client)

    result = usecase.populate_certificate_context(application, application.proceeding)

    assert result.client_address is not None
    assert result.client_address.address_line_1 == "456 Oak Avenue"
    assert result.client_address.town_or_city == "Manchester"
    assert result.client_address.postcode == "M1 2AB"


def test_populate_certificate_context_uses_client_home_address_when_correspondence_address_is_none_and_care_of_recipient_is_set():
    """Test that home address is used when correspondence address is None and client is the correspondence recipient."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Test Firm"
    mock_provider_port.get_office_address.return_value = create_base_office_address()
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    # Only override the specific address fields we're testing
    home_address = create_base_home_address(
        address_line_1="789 Pine Road",
        town_or_city="Liverpool",
        postcode="L1 3CD",
    )
    client = create_base_client(
        home_address=home_address,
        correspondence_address=None,
        is_client_correspondence_recipient=False,
    )
    application = create_base_application(client=client)

    result = usecase.populate_certificate_context(application, application.proceeding)

    assert result.client_address is not None
    assert result.client_address.address_line_1 == "c/o John Smith 789 Pine Road"
    assert result.client_address.town_or_city == "Liverpool"
    assert result.client_address.postcode == "L1 3CD"


def test_populate_certificate_context_populates_provider_fields():
    """Test that firm name and office address are populated correctly."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Jones Legal Services"
    mock_provider_port.get_office_address.return_value = create_base_office_address()
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    application = create_base_application(
        provider=create_base_provider(firm_code="XYZ789")
    )

    result = usecase.populate_certificate_context(application, application.proceeding)

    assert result.firm_name == "Jones Legal Services"
    mock_provider_port.get_firm_name.assert_called_once_with("XYZ789")
    assert result.office_address is not None


def test_populate_certificate_context_raises_exception_on_firm_name_lookup_failure():
    """Test that a fallback is used when firm name lookup fails."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.side_effect = ProviderDetailsRetrievalError(
        "HTTP error occurred while retrieving provider details"
    )
    mock_provider_port.get_office_address.return_value = create_base_office_address()
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    application = create_base_application()

    with pytest.raises(ProviderDetailsRetrievalError):
        usecase.populate_certificate_context(application, application.proceeding)


def test_populate_certificate_context_raises_exception_on_office_address_lookup_failure():
    """Test that a fallback is used when office address lookup fails."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Test Firm Name"
    mock_provider_port.get_office_address.side_effect = ProviderDetailsRetrievalError(
        "HTTP error occurred while retrieving provider details"
    )
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    application = create_base_application()

    with pytest.raises(ProviderDetailsRetrievalError):
        usecase.populate_certificate_context(application, application.proceeding)


def test_populate_certificate_context_populates_proceeding_fields():
    """Test that proceeding fields are mapped correctly."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Test Firm"
    mock_provider_port.get_office_address.return_value = create_base_office_address()
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    proceeding = create_base_proceeding(
        certificate_type="SUBSTANTIVE",
        category_of_law="INQUESTS",
        level_of_service="FULL_REPRESENTATION",
        scope_limitation_heading="FINAL_HEARING",
        scope_description="Limited to final hearing only",
        substantive_cost_limitation=15000,
        proceeding_description="Inquest proceeding",
    )
    application_proceeding = create_base_application_proceeding(
        proceeding=proceeding,
        certificate_start_date=datetime(2026, 7, 1, tzinfo=UTC),
        merits_decision=MeritsDecision.GRANTED,
    )
    application = create_base_application(proceeding=application_proceeding)

    result = usecase.populate_certificate_context(application, application_proceeding)

    assert result.certificate_type == "SUBSTANTIVE"
    assert result.category_of_law == "INQUESTS"
    assert result.level_of_service == "FULL_REPRESENTATION"
    assert result.scope_limitation_heading == "FINAL_HEARING"
    assert result.scope_limitation_description == "Limited to final hearing only"
    assert result.cost_limitation == 15000
    assert result.proceeding_description == "Inquest proceeding"


def test_populate_certificate_context_populates_application_proceeding_date_fields():
    """Test that date fields from ApplicationProceeding are mapped correctly."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Test Firm"
    mock_provider_port.get_office_address.return_value = create_base_office_address()
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    test_date = datetime(2026, 8, 15, tzinfo=UTC)
    application = create_base_application(
        proceeding=create_base_application_proceeding(certificate_start_date=test_date)
    )

    result = usecase.populate_certificate_context(application, application.proceeding)

    assert result.effective_date == test_date.date()
    assert result.date_work_can_commence == test_date.date()
    assert result.date_current_level_of_service_effective == test_date.date()


def test_populate_certificate_context_populates_application_status_fields():
    """Test that application status is mapped correctly."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Test Firm"
    mock_provider_port.get_office_address.return_value = create_base_office_address()
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    application = create_base_application(status="LIVE")

    result = usecase.populate_certificate_context(application, application.proceeding)

    assert result.status == "LIVE"
    assert result.current_proceeding_status == "LIVE"


def test_populate_certificate_context_populates_identifiers_and_dates():
    """LAA reference and date created are read from application/proceeding."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Test Firm"
    mock_provider_port.get_office_address.return_value = create_base_office_address()
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    issue_date = datetime(2026, 7, 15, tzinfo=UTC)
    application = create_base_application(
        laa_reference=98765,
        proceeding=create_base_application_proceeding(
            certificate_issue_date=issue_date
        ),
    )

    result = usecase.populate_certificate_context(application, application.proceeding)

    assert result.laa_reference == 98765
    assert result.date_created == issue_date.date()


def test_populate_certificate_context_populates_default_static_fields():
    """Test that static/default fields are populated correctly."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Test Firm"
    mock_provider_port.get_office_address.return_value = create_base_office_address()
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    application = create_base_application()

    result = usecase.populate_certificate_context(application, application.proceeding)

    assert result.guardian_name == "Not applicable"
    assert result.guardian_address == "Not applicable"
    assert result.client_involvement_type == "Applicant"
    assert result.certificate_limitation == "Not applicable"
    assert result.previous_level_of_service == "Not applicable"
    assert result.reinstatement_date is None
    assert result.end_date is None
    assert result.proceeding_end_date is None


def test_populate_certificate_context_handles_none_certificate_start_date():
    """Test that None certificate_start_date is handled gracefully."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Test Firm"
    mock_provider_port.get_office_address.return_value = create_base_office_address()
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    application = create_base_application(
        proceeding=create_base_application_proceeding(certificate_start_date=None)
    )

    # Should not raise an exception
    result = usecase.populate_certificate_context(application, application.proceeding)

    assert isinstance(result, ApplicationCertificate)

    assert result.effective_date == datetime.now(tz=UTC).date()
    assert result.date_work_can_commence == datetime.now(tz=UTC).date()
    assert result.date_current_level_of_service_effective == datetime.now(tz=UTC).date()


def test_populate_certificate_context_formats_address_with_missing_fields():
    """Test that address formatting handles missing optional fields."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Test Firm"
    mock_provider_port.get_office_address.return_value = create_base_office_address()
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    # Create address with no address_line_2 or county
    home_address = create_base_home_address(
        address_line_1="100 Simple Street",
        address_line_2=None,
        town_or_city="Bristol",
        county=None,
        postcode="BS1 1AA",
    )
    application = create_base_application(
        client=create_base_client(
            home_address=home_address, correspondence_address=None
        )
    )

    result = usecase.populate_certificate_context(application, application.proceeding)

    assert result.client_address is not None
    assert result.client_address.address_line_1 == "100 Simple Street"
    assert result.client_address.town_or_city == "Bristol"
    assert result.client_address.postcode == "BS1 1AA"
    assert result.client_address.address_line_2 is None
    assert result.client_address.county is None


def test_populate_certificate_context_handles_none_correspondence_address():
    """Test that None correspondence address falls back to home address."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Test Firm"
    mock_provider_port.get_office_address.return_value = create_base_office_address()
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    home_address = create_base_home_address(
        address_line_1="Home Street 1",
        postcode="HM1 1AA",
    )
    application = create_base_application(
        client=create_base_client(
            home_address=home_address, correspondence_address=None
        )
    )

    result = usecase.populate_certificate_context(application, application.proceeding)

    # Should use home address
    assert "Home Street 1" == result.client_address.address_line_1
    assert "HM1 1AA" == result.client_address.postcode


def test_populate_certificate_context_handles_single_public_body_correctly():
    """Test that a single public body is handled correctly."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Test Firm"
    mock_provider_port.get_office_address.return_value = create_base_office_address()
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    application = create_base_application(
        public_bodies=[
            create_base_application_public_body(
                public_body=create_base_public_body(public_body_description="Body A")
            )
        ]
    )

    result = usecase.populate_certificate_context(application, application.proceeding)

    assert result.opponent_details == ["Body A"]
    assert len(result.opponent_details) == 1


def test_populate_certificate_context_adds_public_bodies_to_opponent_details():
    """Test that public bodies are concatenated correctly."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Test Firm"
    mock_provider_port.get_office_address.return_value = create_base_office_address()
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    application = create_base_application(
        public_bodies=[
            create_base_application_public_body(
                public_body=create_base_public_body(public_body_description="Body A")
            ),
            create_base_application_public_body(
                public_body=create_base_public_body(public_body_description="Body B")
            ),
        ]
    )

    result = usecase.populate_certificate_context(application, application.proceeding)

    assert result.opponent_details == ["Body A", "Body B"]
    assert len(result.opponent_details) == 2


def test_prepare_context_for_display_formats_fields_correctly():
    """Test that prepare_context_for_display formats enum fields correctly."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Test Firm"
    mock_provider_port.get_office_address.return_value = create_base_office_address()
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    application = create_base_application(
        proceeding=create_base_application_proceeding(
            certificate_type="SUBSTANTIVE",
            status="LIVE",
            category_of_law="INQUESTS",
            current_proceeding_status="LIVE",
            level_of_service="FULL_REPRESENTATION",
            scope_limitation_heading="FINAL_HEARING",
        )
    )

    context = usecase.populate_certificate_context(application, application.proceeding)
    formatted_context = usecase.prepare_context_for_display(context)

    assert formatted_context.certificate_type == "Substantive"
    assert formatted_context.status == "Live"
    assert formatted_context.category_of_law == "Inquests"
    assert formatted_context.current_proceeding_status == "Live"
    assert formatted_context.level_of_service == "Full representation"
    assert formatted_context.scope_limitation_heading == "Final hearing"


def test_populate_certificate_context_uses_office_address_when_correspondence_address_source_is_use_provider_address():
    """Test that the provider's office address is used when correspondence address source is set to USE_PROVIDER_ADDRESS."""
    mock_provider_port = MagicMock()
    mock_provider_port.get_firm_name.return_value = "Test Firm"
    office_address = create_base_office_address(
        address_line_1="123 Provider St",
        town_or_city="Provider City",
        postcode="PC1 2AB",
    )
    mock_provider_port.get_office_address.return_value = office_address
    usecase = CreateCertificateContextUseCase(provider_details_port=mock_provider_port)

    client = create_base_client(
        correspondence_address=None,
        home_address=create_base_home_address(
            address_line_1="456 Home St",
            town_or_city="Home City",
            postcode="HC3 4DE",
        ),
        correspondence_recipient=None,
        correspondence_address_source="USE_PROVIDER_ADDRESS",
    )
    application = create_base_application(client=client)

    result = usecase.populate_certificate_context(application, application.proceeding)

    assert result.client_address.address_line_1 == "123 Provider St"
    assert result.client_address.town_or_city == "Provider City"
    assert result.client_address.postcode == "PC1 2AB"
