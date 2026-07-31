from unittest.mock import MagicMock

import pytest

from app.ports.get_application_port import GetApplicationPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import ApplicationNotFoundError
from app.use_cases.get_application import GetApplicationUseCase
from tests.unit.factories import create_base_application, create_base_provider


def test_execute_raises_application_not_found_error_when_application_not_found():
    get_application_port = MagicMock(spec=GetApplicationPort)
    get_application_port.get_application_by_laa_reference.return_value = None
    port = MagicMock(spec=ProviderDetailsPort)

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=port,
    )

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute("99999")


def test_execute_calls_provider_details_port_with_firm_code():
    get_application_port = MagicMock(spec=GetApplicationPort)
    provider = create_base_provider(firm_code="0A123B", office_id="001")
    get_application_port.get_application_by_laa_reference.return_value = (
        create_base_application(provider=provider)
    )
    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = "Test Firm"

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=port,
    )
    use_case.execute("1")

    port.get_firm_name.assert_called_once_with("0A123B")


def test_execute_returns_application_response_with_firm_name():
    get_application_port = MagicMock(spec=GetApplicationPort)
    get_application_port.get_application_by_laa_reference.return_value = (
        create_base_application()
    )
    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = "Test Firm"

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=port,
    )
    result = use_case.execute("1")

    assert result.provider.firm_name == "Test Firm"


def test_execute_returns_firm_name_as_none_when_port_returns_none():
    get_application_port = MagicMock(spec=GetApplicationPort)
    get_application_port.get_application_by_laa_reference.return_value = (
        create_base_application()
    )
    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = None

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=port,
    )
    result = use_case.execute("1")

    assert result.provider.firm_name is None


def test_execute_returns_correct_account_number():
    get_application_port = MagicMock(spec=GetApplicationPort)
    provider = create_base_provider(office_id="042")
    get_application_port.get_application_by_laa_reference.return_value = (
        create_base_application(provider=provider)
    )
    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = "Test Firm"

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=port,
    )
    result = use_case.execute("1")

    assert result.provider.account_number == "042"


def test_execute_returns_provider_email_in_response():
    get_application_port = MagicMock(spec=GetApplicationPort)
    provider = create_base_provider(email_address="provider@example.com")
    get_application_port.get_application_by_laa_reference.return_value = (
        create_base_application(provider=provider)
    )
    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = "Test Firm"

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=port,
    )
    result = use_case.execute("1")

    assert result.provider.email_address == "provider@example.com"
