from unittest.mock import MagicMock

import pytest

from app.models.application.enums import ProceedingId
from app.models.application.index import (
    Application,
    ApplicationProceeding,
    Client,
    Provider,
)
from app.ports.gov_notify_port import GovNotifyPort
from app.ports.pdf_generation_port import PdfGenerationPort
from app.use_cases.send_grant_email import SendGrantEmailUseCase
from tests.unit.factories import create_base_certificate


@pytest.fixture
def pdf_generation_port() -> MagicMock:
    return MagicMock(spec=PdfGenerationPort)


@pytest.fixture
def gov_notify_port() -> MagicMock:
    return MagicMock(spec=GovNotifyPort)


@pytest.fixture
def application() -> Application:
    proceeding = ApplicationProceeding(laa_reference=1, proceeding_id=ProceedingId.IQOT)
    client = Client(
        client_first_name="Test",
        client_last_name="Client",
        date_of_birth="01-01-1990",
        correspondence_address_source="USE_CLIENT_HOME_ADDRESS",
    )
    provider = Provider(
        firm_code="0A123B", office_id="001", email_address="test@example.com"
    )
    return Application(proceeding=proceeding, provider=provider, client=client)


@pytest.fixture
def certificate_context():
    return create_base_certificate()


@pytest.fixture
def use_case(
    pdf_generation_port: MagicMock,
    gov_notify_port: MagicMock,
) -> SendGrantEmailUseCase:
    return SendGrantEmailUseCase(
        pdf_generation_port=pdf_generation_port,
        gov_notify_port=gov_notify_port,
    )


def test_execute_calls_generate_pdf_with_certificate_template(
    use_case, pdf_generation_port, application, certificate_context
):
    use_case.execute(application, application.proceeding, certificate_context)

    pdf_generation_port.generate_pdf.assert_called_once_with(
        "certificate.html", certificate_context
    )


def test_execute_calls_send_granted_decision_email_with_pdf(
    use_case, pdf_generation_port, gov_notify_port, application, certificate_context
):
    pdf_generation_port.generate_pdf.return_value = b"%PDF-certificate"

    use_case.execute(application, application.proceeding, certificate_context)

    gov_notify_port.send_application_granted_decision_email.assert_called_once_with(
        application,
        application.proceeding,
        "test@example.com",
        b"%PDF-certificate",
    )


def test_execute_raises_exception_when_pdf_generation_fails(
    use_case, pdf_generation_port, application, certificate_context
):
    pdf_generation_port.generate_pdf.side_effect = Exception("PDF generation failed")

    with pytest.raises(Exception, match="PDF generation failed"):
        use_case.execute(application, application.proceeding, certificate_context)


def test_execute_raises_exception_when_email_send_fails(
    use_case, gov_notify_port, application, certificate_context
):
    gov_notify_port.send_application_granted_decision_email.side_effect = Exception(
        "Email send failed"
    )

    with pytest.raises(Exception, match="Email send failed"):
        use_case.execute(application, application.proceeding, certificate_context)
