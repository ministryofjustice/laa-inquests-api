"""Unit tests for send_application_confirmation use case."""

from unittest.mock import Mock
import pytest
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
from app.models.application.enums import AddressSource
from app.models.gov_notify_templates.application_submit_personalisation import (
    NotifyApplicationSubmitTemplatePersonalisation,
)
from app.use_cases.notify.send_application_confirmation import (
    send_application_confirmation,
)
from app.config import Config


def _create_test_application(laa_reference: int = 12345) -> Application:
    """Helper to create a test application with all required relationships."""
    home_address = Address(
        address_id=1,
        address_line_1="123 Test St",
        town_or_city="London",
        postcode="SW1A 1AA",
    )

    client = Client(
        client_id=1,
        client_first_name="Jane",
        client_last_name="Doe",
        date_of_birth="15-06-1985",
        correspondence_address_source=AddressSource.USE_CLIENT_HOME_ADDRESS,
        home_address_id=1,
        home_address=home_address,
        is_client_correspondence_recipient=True,
    )

    deceased = Deceased(
        deceased_id=1,
        client_id=1,
        deceased_first_name="Robert",
        deceased_last_name="Johnson",
        deceased_date_of_birth="01-01-1950",
        deceased_date_of_death="31-12-2025",
        coroners_reference="COR-2025-123",
        further_information="Test info",
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
        laa_reference=laa_reference,
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
        laa_reference=laa_reference,
        public_body_id=PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
        public_body=public_body,
    )

    provider = Provider(provider_id=1, firm_code="ABC123", office_id="001")

    return Application(
        laa_reference=laa_reference,
        client_id=1,
        client=client,
        deceased_id=1,
        deceased=deceased,
        provider_id=1,
        provider=provider,
        proceedings=[application_proceeding],
        public_bodies=[application_public_body],
    )


def test_send_application_confirmation_calls_adapter_with_correct_parameters():
    """
    Test that send_application_confirmation calls the adapter with correct email and data.
    """
    application = _create_test_application(laa_reference=12345)
    mock_adapter = Mock()
    provider_email = "provider@example.com"

    send_application_confirmation(mock_adapter, application, provider_email)

    assert mock_adapter.send_email.call_count == 1

    call_args = mock_adapter.send_email.call_args
    assert call_args.kwargs["email_address"] == "provider@example.com"
    assert (
        call_args.kwargs["template_id"]
        == Config.GOV_NOTIFY_APPLICATION_SUBMIT_TEMPLATE_ID
    )


def test_send_application_confirmation_propagates_adapter_exceptions():
    """
    Test that send_application_confirmation propagates exceptions from the adapter.
    """
    application = _create_test_application()
    mock_adapter = Mock()
    provider_email = "provider@example.com"
    mock_adapter.send_email.side_effect = Exception("GovNotify API error")

    with pytest.raises(Exception) as exc_info:
        send_application_confirmation(mock_adapter, application, provider_email)

    assert "GovNotify API error" in str(exc_info.value)


def test_send_application_confirmation_builds_complete_personalisation():
    """
    Test that send_application_confirmation builds personalisation with all template fields.
    """
    application = _create_test_application(laa_reference=99999)
    mock_adapter = Mock()
    provider_email = "provider@example.com"

    send_application_confirmation(mock_adapter, application, provider_email)

    personalisation = mock_adapter.send_email.call_args.kwargs["personalisation"]

    assert isinstance(personalisation, NotifyApplicationSubmitTemplatePersonalisation)

    assert personalisation.laa_reference == "99999"
    assert personalisation.client_first_name == "Jane"
    assert personalisation.client_last_name == "Doe"
    assert personalisation.deceased_first_name == "Robert"
    assert personalisation.proceeding_description == "Inquest into death"
    assert personalisation.public_body_description == "Department for Transport"
