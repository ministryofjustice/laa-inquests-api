from unittest.mock import MagicMock

import pytest

from app.models.application.enums import AddressSource
from app.models.application.index import Application, Client, Deceased, Provider
from app.ports.get_application_port import GetApplicationPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import ApplicationNotFoundError
from app.use_cases.get_application import GetApplicationUseCase


def _make_application(
    firm_code: str = "0A123B",
    office_id: str = "001",
    email_address: str = "test@example.com",
) -> Application:
    provider = Provider(
        firm_code=firm_code, office_id=office_id, email_address=email_address
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
        coroners_reference="COR-001",
        further_information=None,
        client_relationship_to_deceased="sibling",
    )
    proceeding = Proceeding(
        id=1,
        proceeding_id=ProceedingId.IQOT,
        proceeding_name="Inquest into death",
        proceeding_description="Inquest into death",
        category_of_law="INQUESTS",
        certificate_type="SUBSTANTIVE",
        level_of_service="FULL_REPRESENTATION",
        matter_type="INQUESTS",
        scope_limitation_heading="FINAL_HEARING",
        scope_description="This is the scope description",
        substantive_cost_limitation=10000,
    )
    application_proceeding = ApplicationProceeding(
        laa_reference=1,
        proceeding_id=ProceedingId.IQOT,
        proceeding=proceeding,
    )
    return Application(
        laa_reference=1,
        client=client,
        deceased=deceased,
        provider=provider,
        proceeding=application_proceeding,
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


def test_execute_calls_provider_details_port_with_firm_code():
    get_application_port = MagicMock(spec=GetApplicationPort)
    get_application_port.get_application_by_laa_reference.return_value = (
        _make_application(firm_code="0A123B", office_id="001")
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
        _make_application()
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
        _make_application()
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
    get_application_port.get_application_by_laa_reference.return_value = (
        _make_application(office_id="042")
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
    get_application_port.get_application_by_laa_reference.return_value = (
        _make_application(email_address="provider@example.com")
    )
    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = "Test Firm"

    use_case = GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=port,
    )
    result = use_case.execute("1")

    assert result.provider.email_address == "provider@example.com"
