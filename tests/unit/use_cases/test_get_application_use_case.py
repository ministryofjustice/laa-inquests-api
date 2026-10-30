from unittest.mock import MagicMock

import pytest

from app.models.application.enums import AddressSource
from app.models.application.index import (
    Address,
    AddressResponse,
    PotentialDuplicateApplicationResponse,
)
from app.ports.get_application_port import GetApplicationPort
from app.ports.get_potential_duplicate_applications_port import (
    GetPotentialDuplicateApplicationsPort,
)
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import (
    ApplicationNotFoundError,
    ProviderDetailsRetrievalError,
)
from app.use_cases.get_application import GetApplicationUseCase
from tests.unit.factories import (
    create_base_application,
    create_base_client,
    create_base_provider,
)


def test_execute_raises_application_not_found_error_when_application_not_found():
    get_application_port = MagicMock(spec=GetApplicationPort)
    get_application_port.get_application_by_laa_reference.return_value = None
    provider_details_port = MagicMock(spec=ProviderDetailsPort)
    duplicates_port = MagicMock(spec=GetPotentialDuplicateApplicationsPort)

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=provider_details_port,
        get_potential_duplicate_applications_port=duplicates_port,
    )

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute("99999")


def test_execute_calls_provider_details_port_get_firm_name_with_firm_code():
    get_application_port = MagicMock(spec=GetApplicationPort)
    provider = create_base_provider(firm_code="0A123B", office_id="0U651L")
    get_application_port.get_application_by_laa_reference.return_value = (
        create_base_application(provider=provider)
    )
    provider_details_port = MagicMock(spec=ProviderDetailsPort)
    provider_details_port.get_firm_name.return_value = "Test Firm"
    duplicates_port = MagicMock(spec=GetPotentialDuplicateApplicationsPort)

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=provider_details_port,
        get_potential_duplicate_applications_port=duplicates_port,
    )
    use_case.execute("1")

    provider_details_port.get_firm_name.assert_called_once_with("0A123B")


def test_execute_returns_application_response_with_firm_name():
    get_application_port = MagicMock(spec=GetApplicationPort)
    get_application_port.get_application_by_laa_reference.return_value = (
        create_base_application()
    )
    provider_details_port = MagicMock(spec=ProviderDetailsPort)
    provider_details_port.get_firm_name.return_value = "Test Firm"
    duplicates_port = MagicMock(spec=GetPotentialDuplicateApplicationsPort)

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=provider_details_port,
        get_potential_duplicate_applications_port=duplicates_port,
    )
    result = use_case.execute("1")

    assert result.provider.firm_name == "Test Firm"


def test_execute_raises_exception_when_provider_details_port_get_firm_name_raises_exception():
    get_application_port = MagicMock(spec=GetApplicationPort)
    get_application_port.get_application_by_laa_reference.return_value = (
        create_base_application()
    )
    provider_details_port = MagicMock(spec=ProviderDetailsPort)
    provider_details_port.get_firm_name.side_effect = ProviderDetailsRetrievalError(
        "Provider details service error"
    )
    duplicates_port = MagicMock(spec=GetPotentialDuplicateApplicationsPort)

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=provider_details_port,
        get_potential_duplicate_applications_port=duplicates_port,
    )

    with pytest.raises(ProviderDetailsRetrievalError) as exc_info:
        use_case.execute("1")

    assert str(exc_info.value) == "Provider details service error"


def test_execute_returns_correct_account_number():
    get_application_port = MagicMock(spec=GetApplicationPort)
    provider = create_base_provider(office_id="042")
    get_application_port.get_application_by_laa_reference.return_value = (
        create_base_application(provider=provider)
    )
    provider_details_port = MagicMock(spec=ProviderDetailsPort)
    provider_details_port.get_firm_name.return_value = "Test Firm"
    duplicates_port = MagicMock(spec=GetPotentialDuplicateApplicationsPort)

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=provider_details_port,
        get_potential_duplicate_applications_port=duplicates_port,
    )
    result = use_case.execute("1")

    assert result.provider.account_number == "042"


def test_execute_returns_provider_email_in_response():
    get_application_port = MagicMock(spec=GetApplicationPort)
    provider = create_base_provider(email_address="provider@example.com")
    get_application_port.get_application_by_laa_reference.return_value = (
        create_base_application(provider=provider)
    )
    provider_details_port = MagicMock(spec=ProviderDetailsPort)
    provider_details_port.get_firm_name.return_value = "Test Firm"
    duplicates_port = MagicMock(spec=GetPotentialDuplicateApplicationsPort)

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=provider_details_port,
        get_potential_duplicate_applications_port=duplicates_port,
    )
    result = use_case.execute("1")

    assert result.provider.email_address == "provider@example.com"


def test_execute_calls_provider_details_port_get_office_address_with_office_id():
    get_application_port = MagicMock(spec=GetApplicationPort)
    client = create_base_client(
        correspondence_address_source=AddressSource.USE_PROVIDER_ADDRESS
    )
    get_application_port.get_application_by_laa_reference.return_value = (
        create_base_application(client=client)
    )
    office_address = Address(
        address_line_1="123 Main St",
        address_line_2="Suite 100",
        town_or_city="Anytown",
        county="Anycounty",
        postcode="AB12 3CD",
    )

    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = "Test Firm"
    port.get_office_address.return_value = office_address
    duplicates_port = MagicMock(spec=GetPotentialDuplicateApplicationsPort)

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=port,
        get_potential_duplicate_applications_port=duplicates_port,
    )
    use_case.execute("1")

    port.get_office_address.assert_called_once_with("0U651L")


def test_execute_returns_application_response_with_office_correspondence_address():
    get_application_port = MagicMock(spec=GetApplicationPort)
    client = create_base_client(
        correspondence_address_source=AddressSource.USE_PROVIDER_ADDRESS
    )
    get_application_port.get_application_by_laa_reference.return_value = (
        create_base_application(client=client)
    )
    office_address = Address(
        address_line_1="123 Main St",
        address_line_2="Suite 100",
        town_or_city="Anytown",
        county="Anycounty",
        postcode="AB12 3CD",
    )

    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = "Test Firm"
    port.get_office_address.return_value = office_address
    duplicates_port = MagicMock(spec=GetPotentialDuplicateApplicationsPort)

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=port,
        get_potential_duplicate_applications_port=duplicates_port,
    )
    result = use_case.execute("1")

    assert result.client.correspondence_address == AddressResponse(
        **office_address.__dict__
    )


def test_execute_returns_application_response_with_office_correspondence_address_when_no_fixed_abode():
    get_application_port = MagicMock(spec=GetApplicationPort)
    client = create_base_client(
        correspondence_address_source=AddressSource.USE_PROVIDER_ADDRESS
    )
    get_application_port.get_application_by_laa_reference.return_value = (
        create_base_application(client=client)
    )
    office_address = Address(
        address_line_1="123 Main St",
        address_line_2="Suite 100",
        town_or_city="Anytown",
        county="Anycounty",
        postcode="AB12 3CD",
    )

    provider_details_port = MagicMock(spec=ProviderDetailsPort)
    provider_details_port.get_firm_name.return_value = "Test Firm"
    provider_details_port.get_office_address.return_value = office_address
    duplicates_port = MagicMock(spec=GetPotentialDuplicateApplicationsPort)

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=provider_details_port,
        get_potential_duplicate_applications_port=duplicates_port,
    )
    result = use_case.execute("1")

    assert result.client.correspondence_address == AddressResponse(
        **office_address.__dict__
    )


def test_execute_raises_exception_when_provider_details_port_get_office_address_raises_exception():
    get_application_port = MagicMock(spec=GetApplicationPort)
    client = create_base_client(
        correspondence_address_source=AddressSource.USE_PROVIDER_ADDRESS
    )
    get_application_port.get_application_by_laa_reference.return_value = (
        create_base_application(client=client)
    )
    provider_details_port = MagicMock(spec=ProviderDetailsPort)
    provider_details_port.get_firm_name.return_value = "Test Firm"
    provider_details_port.get_office_address.side_effect = (
        ProviderDetailsRetrievalError("Provider details service error")
    )
    duplicates_port = MagicMock(spec=GetPotentialDuplicateApplicationsPort)

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=provider_details_port,
        get_potential_duplicate_applications_port=duplicates_port,
    )

    with pytest.raises(ProviderDetailsRetrievalError) as exc_info:
        use_case.execute("1")

    assert str(exc_info.value) == "Provider details service error"


def test_execute_returns_empty_list_when_get_potential_duplicates_handles_empty_ids_list():
    get_application_port = MagicMock(spec=GetApplicationPort)
    client = create_base_client()
    get_application_port.get_application_by_laa_reference.return_value = (
        create_base_application(client=client)
    )

    provider_details_port = MagicMock(spec=ProviderDetailsPort)
    provider_details_port.get_firm_name.return_value = "Test Firm"
    provider_details_port.get_office_address.return_value = Address(
        address_line_1="123 Main St",
        address_line_2="Suite 100",
        town_or_city="Anytown",
        county="Anycounty",
        postcode="AB12 3CD",
    )
    duplicates_port = MagicMock(spec=GetPotentialDuplicateApplicationsPort)
    duplicates_port.get_potential_duplicate_application_ids.return_value = []

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=provider_details_port,
        get_potential_duplicate_applications_port=duplicates_port,
    )

    result = use_case.execute("1")

    duplicates_port.get_duplicate_applications_by_ids.assert_called_once_with([])
    assert result.potential_duplicate_applications == []


def test_execute_returns_potential_duplicates_when_get_potential_duplicates_returns_non_empty():
    get_application_port = MagicMock(spec=GetApplicationPort)
    client = create_base_client()
    application = create_base_application(client=client)
    get_application_port.get_application_by_laa_reference.return_value = application

    provider_details_port = MagicMock(spec=ProviderDetailsPort)
    provider_details_port.get_firm_name.return_value = "Test Firm"
    provider_details_port.get_office_address.return_value = Address(
        address_line_1="123 Main St",
        address_line_2="Suite 100",
        town_or_city="Anytown",
        county="Anycounty",
        postcode="AB12 3CD",
    )
    duplicates_port = MagicMock(spec=GetPotentialDuplicateApplicationsPort)
    duplicates_port.get_potential_duplicate_application_ids.return_value = [1]
    duplicates_port.get_duplicate_applications_by_ids.return_value = [application]

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=provider_details_port,
        get_potential_duplicate_applications_port=duplicates_port,
    )

    result = use_case.execute("1")

    duplicates_port.get_duplicate_applications_by_ids.assert_called_once_with([1])
    assert result.potential_duplicate_applications == [
        PotentialDuplicateApplicationResponse(
            laa_reference=application.laa_reference,
            status=application.overall_decision,
        )
    ]


def test_execute_returns_multiple_potential_duplicates_when_get_potential_duplicates_returns_non_empty():
    get_application_port = MagicMock(spec=GetApplicationPort)
    client = create_base_client()
    first_application = create_base_application(client=client)
    second_application = create_base_application(client=client)
    get_application_port.get_application_by_laa_reference.return_value = (
        first_application
    )

    provider_details_port = MagicMock(spec=ProviderDetailsPort)
    provider_details_port.get_firm_name.return_value = "Test Firm"
    provider_details_port.get_office_address.return_value = Address(
        address_line_1="123 Main St",
        address_line_2="Suite 100",
        town_or_city="Anytown",
        county="Anycounty",
        postcode="AB12 3CD",
    )
    duplicates_port = MagicMock(spec=GetPotentialDuplicateApplicationsPort)
    duplicates_port.get_potential_duplicate_application_ids.return_value = [1, 2]
    duplicates_port.get_duplicate_applications_by_ids.return_value = [
        first_application,
        second_application,
    ]

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=provider_details_port,
        get_potential_duplicate_applications_port=duplicates_port,
    )

    result = use_case.execute("1")

    duplicates_port.get_duplicate_applications_by_ids.assert_called_once_with([1, 2])
    assert result.potential_duplicate_applications == [
        PotentialDuplicateApplicationResponse(
            laa_reference=first_application.laa_reference,
            status=first_application.overall_decision,
        ),
        PotentialDuplicateApplicationResponse(
            laa_reference=second_application.laa_reference,
            status=second_application.overall_decision,
        ),
    ]


def test_execute_returns_empty_potential_duplicates_list_when_duplicate_ids_found_but_no_applications_returned():
    get_application_port = MagicMock(spec=GetApplicationPort)
    get_application_port.get_application_by_laa_reference.return_value = (
        create_base_application()
    )
    provider_details_port = MagicMock(spec=ProviderDetailsPort)
    provider_details_port.get_firm_name.return_value = "Test Firm"
    duplicates_port = MagicMock(spec=GetPotentialDuplicateApplicationsPort)
    duplicates_port.get_potential_duplicate_application_ids.return_value = [1]
    duplicates_port.get_duplicate_applications_by_ids.return_value = []

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=provider_details_port,
        get_potential_duplicate_applications_port=duplicates_port,
    )

    result = use_case.execute("1")

    duplicates_port.get_duplicate_applications_by_ids.assert_called_once_with([1])
    assert result.potential_duplicate_applications == []
