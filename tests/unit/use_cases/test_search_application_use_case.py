from unittest.mock import MagicMock

from app.models.application.enums import AddressSource, MeritsDecision
from app.models.application.index import Application, Client, Deceased, Provider
from app.ports.provider_details_port import ProviderDetailsPort
from app.ports.search_application_port import SearchApplicationPort
from app.use_cases.search_application import SearchApplicationUseCase


def _make_application(
    firm_code: str = "0A123B",
    status: str = "LIVE",
) -> Application:
    provider = Provider(
        firm_code=firm_code,
        office_id="001",
        email_address="test@example.com",
    )
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
        coroners_reference="COR-2025-001",
        further_information=None,
        client_relationship_to_deceased="sibling",
    )
    return Application(
        laa_reference=1,
        status=status,
        client=client,
        deceased=deceased,
        provider=provider,
    )


def _make_use_case(
    application: Application | None = None,
    firm_name: str = "Test Firm",
) -> SearchApplicationUseCase:
    search_port = MagicMock(spec=SearchApplicationPort)
    search_port.search_applications.return_value = [application] if application else []
    provider_port = MagicMock(spec=ProviderDetailsPort)
    provider_port.get_firm_name.return_value = firm_name
    return SearchApplicationUseCase(
        search_application_port=search_port,
        provider_details_port=provider_port,
    )


def test_execute_returns_empty_list_when_no_match():
    use_case = _make_use_case(application=None)

    assert use_case.execute("1") == []


def test_execute_normalises_reference_by_stripping_whitespace_before_lookup():
    search_port = MagicMock(spec=SearchApplicationPort)
    search_port.search_applications.return_value = []
    provider_port = MagicMock(spec=ProviderDetailsPort)
    use_case = SearchApplicationUseCase(
        search_application_port=search_port,
        provider_details_port=provider_port,
    )

    use_case.execute("  1  ")

    search_port.search_applications.assert_called_once_with("1")


def test_execute_calls_provider_details_port_with_firm_code():
    application = _make_application(firm_code="0A123B")
    search_port = MagicMock(spec=SearchApplicationPort)
    search_port.search_applications.return_value = [application]
    provider_port = MagicMock(spec=ProviderDetailsPort)
    provider_port.get_firm_name.return_value = "Test Firm"
    use_case = SearchApplicationUseCase(
        search_application_port=search_port,
        provider_details_port=provider_port,
    )

    use_case.execute("1")

    provider_port.get_firm_name.assert_called_once_with("0A123B")


def test_execute_returns_response_with_all_required_fields():
    application = _make_application(firm_code="0A123B", status="LIVE")
    use_case = _make_use_case(application=application, firm_name="My Firm")

    results = use_case.execute("1")

    assert len(results) == 1
    result = results[0]
    assert result.laa_reference == 1
    assert result.client_first_name == "Test"
    assert result.client_last_name == "User"
    assert result.client_date_of_birth == "2000-01-01"
    assert result.date_submitted == application.created_at
    assert result.firm_name == "My Firm"
    assert result.firm_number == "0A123B"
    assert result.overall_decision == MeritsDecision.PENDING
