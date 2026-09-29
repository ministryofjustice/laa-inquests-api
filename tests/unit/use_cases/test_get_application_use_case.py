from unittest.mock import MagicMock

import pytest

from app.models.application.enums import AddressSource
from app.models.application.index import AddressResponse
from app.ports.get_application_port import GetApplicationPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import (
    ApplicationNotFoundError,
    ProviderDetailsRetrievalError,
)
from app.use_cases.get_application import GetApplicationUseCase
from tests.factories.builders import (
    build_application,
    build_client,
    build_office_address,
    build_provider,
)


def _provider_office_address():
    return build_office_address(
        address_line_2="Suite 100",
        town_or_city="Anytown",
        county="Anycounty",
        postcode="AB12 3CD",
    )


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


def test_execute_calls_provider_details_port_get_firm_name_with_firm_code():
    get_application_port = MagicMock(spec=GetApplicationPort)
    provider = build_provider(firm_code="0A123B", office_id="0U651L")
    get_application_port.get_application_by_laa_reference.return_value = (
        build_application(provider=provider)
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
        build_application()
    )
    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = "Test Firm"

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=port,
    )
    result = use_case.execute("1")

    assert result.provider.firm_name == "Test Firm"


def test_execute_raises_exception_when_provider_details_port_get_firm_name_raises_exception():
    get_application_port = MagicMock(spec=GetApplicationPort)
    get_application_port.get_application_by_laa_reference.return_value = (
        build_application()
    )
    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.side_effect = ProviderDetailsRetrievalError(
        "Provider details service error"
    )

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=port,
    )

    with pytest.raises(ProviderDetailsRetrievalError) as exc_info:
        use_case.execute("1")

    assert str(exc_info.value) == "Provider details service error"


def test_execute_returns_correct_account_number():
    get_application_port = MagicMock(spec=GetApplicationPort)
    provider = build_provider(office_id="042")
    get_application_port.get_application_by_laa_reference.return_value = (
        build_application(provider=provider)
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
    provider = build_provider(email_address="provider@example.com")
    get_application_port.get_application_by_laa_reference.return_value = (
        build_application(provider=provider)
    )
    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = "Test Firm"

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=port,
    )
    result = use_case.execute("1")

    assert result.provider.email_address == "provider@example.com"


def test_execute_calls_provider_details_port_get_office_address_with_office_id():
    get_application_port = MagicMock(spec=GetApplicationPort)
    client = build_client(
        correspondence_address_source=AddressSource.USE_PROVIDER_ADDRESS
    )
    get_application_port.get_application_by_laa_reference.return_value = (
        build_application(client=client)
    )
    office_address = _provider_office_address()

    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = "Test Firm"
    port.get_office_address.return_value = office_address

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=port,
    )
    use_case.execute("1")

    port.get_office_address.assert_called_once_with("0U651L")


def test_execute_returns_application_response_with_office_correspondence_address():
    get_application_port = MagicMock(spec=GetApplicationPort)
    client = build_client(
        correspondence_address_source=AddressSource.USE_PROVIDER_ADDRESS
    )
    get_application_port.get_application_by_laa_reference.return_value = (
        build_application(client=client)
    )
    office_address = _provider_office_address()

    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = "Test Firm"
    port.get_office_address.return_value = office_address

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=port,
    )
    result = use_case.execute("1")

    assert result.client.correspondence_address == AddressResponse(
        **office_address.__dict__
    )


def test_execute_returns_application_response_with_office_correspondence_address_when_no_fixed_abode():
    get_application_port = MagicMock(spec=GetApplicationPort)
    client = build_client(
        correspondence_address_source=AddressSource.USE_PROVIDER_ADDRESS
    )
    get_application_port.get_application_by_laa_reference.return_value = (
        build_application(client=client)
    )
    office_address = _provider_office_address()

    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = "Test Firm"
    port.get_office_address.return_value = office_address

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=port,
    )
    result = use_case.execute("1")

    assert result.client.correspondence_address == AddressResponse(
        **office_address.__dict__
    )


def test_execute_raises_exception_when_provider_details_port_get_office_address_raises_exception():
    get_application_port = MagicMock(spec=GetApplicationPort)
    client = build_client(
        correspondence_address_source=AddressSource.USE_PROVIDER_ADDRESS
    )
    get_application_port.get_application_by_laa_reference.return_value = (
        build_application(client=client)
    )
    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = "Test Firm"
    port.get_office_address.side_effect = ProviderDetailsRetrievalError(
        "Provider details service error"
    )

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=port,
    )

    with pytest.raises(ProviderDetailsRetrievalError) as exc_info:
        use_case.execute("1")

    assert str(exc_info.value) == "Provider details service error"
