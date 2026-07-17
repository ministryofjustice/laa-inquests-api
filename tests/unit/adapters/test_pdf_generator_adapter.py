"""Unit tests for WeasyPrint adapter."""

from datetime import date
from io import BytesIO

import pytest
from pypdf import PdfReader

from app.adapters.pdf_generator_adapter import PdfGeneratorAdapter
from app.models.application.index import Address
from app.models.application.certificate import ApplicationCertificate


def _sample_context() -> ApplicationCertificate:
    """Build a minimal, valid ApplicationCertificate context for template rendering."""
    return ApplicationCertificate(
        client_name="Jane Doe",
        client_address=Address(
            address_line_1="1 High Street",
            town_or_city="London",
            postcode="SW1A 1AA",
        ),
        firm_name="Test Firm Ltd",
        office_address="Office address\nLondon",
        opponent_details="Department for Transport",
        laa_reference=12345,
        date_created=date(2026, 7, 15),
        certificate_type="SUBSTANTIVE",
        status="LIVE",
        effective_date=date(2026, 7, 15),
        cost_limitation="15000",
        care_order_description="Inquest into death",
        category_of_law="INQUESTS",
        current_proceeding_status="LIVE",
        date_work_can_commence=date(2026, 7, 15),
        level_of_service="FULL_REPRESENTATION",
        date_current_level_of_service_effective=date(2026, 7, 15),
        scope_limitation_heading="FINAL_HEARING",
        scope_limitation_description="Limited to final hearing only",
    )


def test_generate_pdf_returns_bytes():
    """Test that generate_pdf returns bytes."""
    adapter = PdfGeneratorAdapter()
    result = adapter.generate_pdf("certificate.html", _sample_context())

    assert isinstance(result, bytes)
    assert len(result) > 0


def test_generate_pdf_returns_valid_pdf():
    """Test that generate_pdf returns content starting with PDF magic bytes."""
    adapter = PdfGeneratorAdapter()
    result = adapter.generate_pdf("certificate.html", _sample_context())

    # PDF files start with %PDF
    assert result.startswith(b"%PDF")


def test_generate_pdf_returns_pdf_with_correct_content():
    """Test that generate_pdf returns a PDF containing expected content."""
    adapter = PdfGeneratorAdapter()
    result = adapter.generate_pdf("certificate.html", _sample_context())

    reader = PdfReader(BytesIO(result))
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "Jane Doe" in pdf_text
    assert "Test Firm Ltd" in pdf_text
    assert "Inquest into death" in pdf_text
    assert "{{" not in pdf_text


def test_generate_pdf_template_not_found_raises_error():
    """Test that requesting a non-existent template raises an error."""
    adapter = PdfGeneratorAdapter()

    with pytest.raises(Exception):
        adapter.generate_pdf("nonexistent_template.html", {})
