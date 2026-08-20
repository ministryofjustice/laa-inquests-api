from unittest.mock import MagicMock

import pytest

from app.ports.gov_notify_port import GovNotifyPort
from app.ports.pdf_generation_port import PdfGenerationPort
from app.use_cases.send_grant_letter import SendGrantLetterUseCase
from tests.unit.factories import create_base_certificate


@pytest.fixture
def pdf_generation_port() -> MagicMock:
    return MagicMock(spec=PdfGenerationPort)


@pytest.fixture
def gov_notify_port() -> MagicMock:
    return MagicMock(spec=GovNotifyPort)


@pytest.fixture
def certificate_context():
    return create_base_certificate()


@pytest.fixture
def use_case(
    pdf_generation_port: MagicMock,
    gov_notify_port: MagicMock,
) -> SendGrantLetterUseCase:
    return SendGrantLetterUseCase(
        pdf_generation_port=pdf_generation_port,
        gov_notify_port=gov_notify_port,
    )


def test_execute_calls_generate_print_letter_pdf_with_certificate_context(
    use_case, pdf_generation_port, certificate_context
):
    use_case.execute(certificate_context)

    pdf_generation_port.generate_print_letter_pdf.assert_called_once_with(
        certificate_context
    )


def test_execute_calls_send_precompiled_letter_with_reference_and_pdf(
    use_case, pdf_generation_port, gov_notify_port, certificate_context
):
    pdf_generation_port.generate_print_letter_pdf.return_value = b"%PDF-combined"

    use_case.execute(certificate_context)

    gov_notify_port.send_precompiled_letter.assert_called_once_with(
        str(certificate_context.laa_reference),
        b"%PDF-combined",
    )


def test_execute_raises_exception_when_pdf_generation_fails(
    use_case, pdf_generation_port, certificate_context
):
    pdf_generation_port.generate_print_letter_pdf.side_effect = Exception(
        "PDF generation failed"
    )

    with pytest.raises(Exception, match="PDF generation failed"):
        use_case.execute(certificate_context)


def test_execute_raises_exception_when_send_precompiled_letter_fails(
    use_case, gov_notify_port, certificate_context
):
    gov_notify_port.send_precompiled_letter.side_effect = Exception(
        "Notify letter failed"
    )

    with pytest.raises(Exception, match="Notify letter failed"):
        use_case.execute(certificate_context)
