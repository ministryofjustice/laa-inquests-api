"""Unit tests for GenerateDemoPdfUseCase."""

from unittest.mock import MagicMock

from app.use_cases.generate_demo_pdf import GenerateDemoPdfUseCase


def test_execute_calls_pdf_generation_port_with_correct_template_and_context():
    """Test that execute calls the port with the correct template and context."""
    mock_port = MagicMock()
    mock_port.generate_pdf.return_value = b"%PDF-mock-content"
    use_case = GenerateDemoPdfUseCase(pdf_generation_port=mock_port)

    result = use_case.execute()

    mock_port.generate_pdf.assert_called_once_with(
        "govuk_header_demo.html", {"header_text": "Example GOV.UK Header"}
    )
    assert result == b"%PDF-mock-content"


def test_execute_returns_bytes_from_port():
    """Test that execute returns the bytes returned by the port."""
    expected_pdf = b"%PDF-1.7\ntest content"
    mock_port = MagicMock()
    mock_port.generate_pdf.return_value = expected_pdf
    use_case = GenerateDemoPdfUseCase(pdf_generation_port=mock_port)

    result = use_case.execute()

    assert result == expected_pdf
    assert isinstance(result, bytes)
