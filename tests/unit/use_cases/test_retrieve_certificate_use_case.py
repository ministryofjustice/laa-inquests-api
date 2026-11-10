from unittest.mock import MagicMock

import pytest

from app.models.application.certificate import ApplicationCertificate
from app.models.application.enums import MeritsDecision
from app.models.application.index import Application, ApplicationProceeding
from app.ports.get_application_port import GetApplicationPort
from app.use_cases.create_certificate_context import CreateCertificateContextUseCase
from app.use_cases.exceptions import (
    ApplicationNotFoundError,
    ApplicationNotGrantedError,
)
from app.use_cases.retrieve_certificate import RetrieveCertificateUseCase
from tests.unit.factories import (
    create_base_application,
    create_base_application_proceeding,
    create_base_client,
    create_base_home_address,
    create_base_office_address,
)


def _make_application() -> Application:
    application = MagicMock(spec=Application)
    application.laa_reference = "INQ-123-REF"
    application.proceeding = MagicMock(spec=ApplicationProceeding)
    application.overall_decision = MeritsDecision.GRANTED
    return application


def test_execute_calls_get_application_port_with_laa_reference():
    get_application_port = MagicMock(spec=GetApplicationPort)
    application = _make_application()
    get_application_port.get_application_by_laa_reference.return_value = application
    create_certificate_context_use_case = MagicMock(
        spec=CreateCertificateContextUseCase
    )
    create_certificate_context_use_case.populate_certificate_context.return_value = (
        MagicMock(spec=ApplicationCertificate)
    )

    use_case = RetrieveCertificateUseCase(
        get_application_port=get_application_port,
        create_certificate_context_use_case=create_certificate_context_use_case,
    )

    use_case.execute("123")

    get_application_port.get_application_by_laa_reference.assert_called_once_with("123")


def test_execute_returns_populated_certificate_context():
    get_application_port = MagicMock(spec=GetApplicationPort)
    application = _make_application()
    get_application_port.get_application_by_laa_reference.return_value = application
    certificate_context = MagicMock(spec=ApplicationCertificate)
    create_certificate_context_use_case = MagicMock(
        spec=CreateCertificateContextUseCase
    )
    create_certificate_context_use_case.populate_certificate_context.return_value = (
        certificate_context
    )

    use_case = RetrieveCertificateUseCase(
        get_application_port=get_application_port,
        create_certificate_context_use_case=create_certificate_context_use_case,
    )

    result = use_case.execute("123")

    assert result is certificate_context
    create_certificate_context_use_case.populate_certificate_context.assert_called_once_with(
        application,
        application.proceeding,
    )


def test_execute_raises_application_not_found_error_when_application_is_missing():
    get_application_port = MagicMock(spec=GetApplicationPort)
    get_application_port.get_application_by_laa_reference.return_value = None
    create_certificate_context_use_case = MagicMock(
        spec=CreateCertificateContextUseCase
    )

    use_case = RetrieveCertificateUseCase(
        get_application_port=get_application_port,
        create_certificate_context_use_case=create_certificate_context_use_case,
    )

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute("99999")

    create_certificate_context_use_case.populate_certificate_context.assert_not_called()


@pytest.mark.parametrize(
    "overall_decision", [MeritsDecision.SUBMITTED, MeritsDecision.REFUSED]
)
def test_execute_raises_application_not_granted_error_when_application_not_granted(
    overall_decision,
):
    get_application_port = MagicMock(spec=GetApplicationPort)
    application = _make_application()
    application.overall_decision = overall_decision
    get_application_port.get_application_by_laa_reference.return_value = application
    create_certificate_context_use_case = MagicMock(
        spec=CreateCertificateContextUseCase
    )

    use_case = RetrieveCertificateUseCase(
        get_application_port=get_application_port,
        create_certificate_context_use_case=create_certificate_context_use_case,
    )

    with pytest.raises(ApplicationNotGrantedError):
        use_case.execute("123")

    create_certificate_context_use_case.populate_certificate_context.assert_not_called()


def test_returns_certificate_context_with_client_address_without_double_recipient_name():
    get_application_port = MagicMock(spec=GetApplicationPort)
    application = create_base_application(
        client=create_base_client(
            home_address=create_base_home_address(address_line_1="789 Pine Road"),
            correspondence_address=None,
            correspondence_recipient_name="John Smith",
        ),
        proceeding=create_base_application_proceeding(
            merits_decision=MeritsDecision.GRANTED
        ),
    )
    get_application_port.get_application_by_laa_reference.return_value = application
    provider_details_port = MagicMock()
    provider_details_port.get_firm_name.return_value = "Test Firm"
    provider_details_port.get_office_address.return_value = create_base_office_address()

    use_case = RetrieveCertificateUseCase(
        get_application_port=get_application_port,
        create_certificate_context_use_case=CreateCertificateContextUseCase(
            provider_details_port=provider_details_port
        ),
    )

    use_case.execute(application.laa_reference)
    result = use_case.execute(application.laa_reference)

    assert result.client_address.address_line_1 == "c/o John Smith 789 Pine Road"
    assert application.client.home_address.address_line_1 == "789 Pine Road"
