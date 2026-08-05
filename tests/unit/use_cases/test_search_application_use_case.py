from unittest.mock import MagicMock

import pytest

from app.models.application.enums import MeritsDecision
from app.models.application.index import Application
from app.ports.provider_details_port import ProviderDetailsPort
from app.ports.search_application_port import SearchApplicationPort
from app.use_cases.exceptions import ProviderDetailsRetrievalError
from app.use_cases.search_application import SearchApplicationUseCase
from tests.unit.factories import create_base_application, create_base_provider


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

    assert use_case.execute("1", "0A123B") == []


def test_execute_normalises_reference_by_stripping_whitespace_before_lookup():
    search_port = MagicMock(spec=SearchApplicationPort)
    search_port.search_applications.return_value = []
    provider_port = MagicMock(spec=ProviderDetailsPort)
    use_case = SearchApplicationUseCase(
        search_application_port=search_port,
        provider_details_port=provider_port,
    )

    use_case.execute("  1  ", "0A123B")

    search_port.search_applications.assert_called_once_with("1", "0A123B")


def test_execute_passes_firm_code_to_search_port():
    search_port = MagicMock(spec=SearchApplicationPort)
    search_port.search_applications.return_value = []
    provider_port = MagicMock(spec=ProviderDetailsPort)
    use_case = SearchApplicationUseCase(
        search_application_port=search_port,
        provider_details_port=provider_port,
    )

    use_case.execute("1", "ZZ999Z")

    search_port.search_applications.assert_called_once_with("1", "ZZ999Z")


def test_execute_calls_provider_details_port_with_firm_code():
    provider = create_base_provider(firm_code="0A123B")
    application = create_base_application(provider=provider)
    search_port = MagicMock(spec=SearchApplicationPort)
    search_port.search_applications.return_value = [application]
    provider_port = MagicMock(spec=ProviderDetailsPort)
    provider_port.get_firm_name.return_value = "Test Firm"
    use_case = SearchApplicationUseCase(
        search_application_port=search_port,
        provider_details_port=provider_port,
    )

    use_case.execute("1", "0A123B")

    provider_port.get_firm_name.assert_called_once_with("0A123B")


def test_execute_raises_provider_details_retrieval_error_when_get_firm_name_raises_exception():
    application = create_base_application()
    search_port = MagicMock(spec=SearchApplicationPort)
    search_port.search_applications.return_value = [application]
    provider_port = MagicMock(spec=ProviderDetailsPort)
    provider_port.get_firm_name.side_effect = ProviderDetailsRetrievalError(
        "HTTP error occurred while retrieving provider details"
    )
    use_case = SearchApplicationUseCase(
        search_application_port=search_port,
        provider_details_port=provider_port,
    )
    with pytest.raises(ProviderDetailsRetrievalError):
        use_case.execute("1", "0A123B")


def test_execute_returns_response_with_all_required_fields():
    provider = create_base_provider(firm_code="0A123B")
    application = create_base_application(
        laa_reference=1, provider=provider, status="LIVE"
    )
    use_case = _make_use_case(application=application, firm_name="My Firm")

    results = use_case.execute("1", "0A123B")

    assert len(results) == 1
    result = results[0]
    assert result.laa_reference == 1
    assert result.client_first_name == "Jane"
    assert result.client_last_name == "Doe"
    assert result.client_date_of_birth == "15-06-1985"
    assert result.date_submitted == application.created_at
    assert result.firm_name == "My Firm"
    assert result.firm_number == "0A123B"
    assert result.overall_decision == MeritsDecision.PENDING
