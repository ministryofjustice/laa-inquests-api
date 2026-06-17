import pytest
from unittest.mock import MagicMock

from app.models.application.index import Application, Client, Deceased, Provider
from app.models.application.enums import AddressSource
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.read_application import ReadApplicationUseCase
from app.use_cases.exceptions import ApplicationNotFoundError


def _make_application(
    firm_code: str = "0A123B", office_id: str = "001", email: str = "test@example.com"
) -> Application:
    provider = Provider(firm_code=firm_code, office_id=office_id, email=email)
    client = Client(
        client_id=1,
        client_first_name="Test",
        client_last_name="User",
        date_of_birth="2000-01-01",
        correspondence_address_source=AddressSource.USE_CLIENT_HOME_ADDRESS,
    )
    deceased = Deceased(
        deceased_id=1,
        client_id=1,
        deceased_first_name="Test",
        deceased_last_name="Deceased",
        deceased_date_of_birth="1990-01-01",
        deceased_date_of_death="2025-01-01",
        coroners_reference="COR-001",
        further_information=None,
        client_relationship_to_deceased="sibling",
    )
    return Application(
        laa_reference=1,
        client=client,
        deceased=deceased,
        provider=provider,
    )


def test_execute_raises_application_not_found_error_when_application_not_found():
    session = MagicMock()
    session.get.return_value = None
    port = MagicMock(spec=ProviderDetailsPort)

    use_case = ReadApplicationUseCase(session=session, provider_details_port=port)

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute("99999")


def test_execute_calls_provider_details_port_with_firm_code():
    session = MagicMock()
    session.get.return_value = _make_application(firm_code="0A123B", office_id="001")
    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = "Test Firm"

    use_case = ReadApplicationUseCase(session=session, provider_details_port=port)
    use_case.execute("1")

    port.get_firm_name.assert_called_once_with("0A123B")


def test_execute_returns_application_response_with_firm_name():
    session = MagicMock()
    session.get.return_value = _make_application()
    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = "Test Firm"

    use_case = ReadApplicationUseCase(session=session, provider_details_port=port)
    result = use_case.execute("1")

    assert result.provider.firm_name == "Test Firm"


def test_execute_returns_firm_name_as_none_when_port_returns_none():
    session = MagicMock()
    session.get.return_value = _make_application()
    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = None

    use_case = ReadApplicationUseCase(session=session, provider_details_port=port)
    result = use_case.execute("1")

    assert result.provider.firm_name is None


def test_execute_returns_correct_account_number():
    session = MagicMock()
    session.get.return_value = _make_application(office_id="042")
    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = "Test Firm"

    use_case = ReadApplicationUseCase(session=session, provider_details_port=port)
    result = use_case.execute("1")

    assert result.provider.account_number == "042"


def test_execute_returns_provider_email_in_response():
    session = MagicMock()
    session.get.return_value = _make_application(email="provider@example.com")
    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = "Test Firm"

    use_case = ReadApplicationUseCase(session=session, provider_details_port=port)
    result = use_case.execute("1")

    assert result.provider.email == "provider@example.com"
