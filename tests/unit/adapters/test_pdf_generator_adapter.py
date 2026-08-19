from datetime import date
from io import BytesIO

import pytest
from jinja2 import TemplateNotFound
from pypdf import PdfReader

from app.adapters.pdf_generator_adapter import PdfGeneratorAdapter
from app.models.application.certificate import ApplicationCertificate
from app.models.application.index import Address
from tests.unit.factories import create_base_office_address


def _sample_context() -> ApplicationCertificate:
    """Build a minimal, valid ApplicationCertificate context for template rendering."""
    return ApplicationCertificate(
        client_name="Jane Doe",
        client_address=Address(
            address_line_1="1 High Street",
            address_line_2="Westminster",
            town_or_city="London",
            county="Greater London",
            postcode="SW1A 1AA",
        ),
        firm_name="Test Firm Ltd",
        office_address=create_base_office_address(),
        opponent_details=["Department for Transport"],
        laa_reference=12345,
        date_created=date(2026, 7, 15),
        certificate_type="SUBSTANTIVE",
        status="LIVE",
        effective_date=date(2026, 7, 15),
        cost_limitation=15000,
        cost_limitation_effective_date=date(1057, 7, 15),
        end_date=date(2324, 7, 15),
        proceeding_name="Inquest into death",
        proceeding_description="Inquest into death",
        category_of_law="INQUESTS",
        current_proceeding_status="LIVE",
        date_work_can_commence=date(2026, 7, 15),
        level_of_service="FULL_REPRESENTATION",
        date_current_level_of_service_effective=date(2026, 7, 15),
        scope_limitation_heading="FINAL_HEARING",
        scope_limitation_description="Limited to final hearing only",
    )


@pytest.fixture(scope="module")
def certificate_pdf() -> bytes:
    """Generate the certificate PDF once for all tests that need it."""
    adapter = PdfGeneratorAdapter()
    return adapter.generate_pdf("certificate.html", _sample_context())


@pytest.fixture(scope="module")
def print_letter_pdf() -> bytes:
    """Generate the print letter PDF once for all tests that need it."""
    adapter = PdfGeneratorAdapter()
    return adapter.generate_print_letter_pdf(_sample_context())


def test_generate_pdf_returns_bytes(certificate_pdf):
    """Test that generate_pdf returns bytes."""
    assert isinstance(certificate_pdf, bytes)
    assert len(certificate_pdf) > 0


def test_generate_pdf_returns_valid_pdf(certificate_pdf):
    """Test that generate_pdf returns content starting with PDF magic bytes."""
    assert certificate_pdf.startswith(b"%PDF")


def test_generate_pdf_returns_pdf_with_correct_content(certificate_pdf):
    """Test that generate_pdf returns a PDF containing expected content."""
    reader = PdfReader(BytesIO(certificate_pdf))
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "Jane Doe" in pdf_text
    assert "Test Firm Ltd" in pdf_text
    assert "Inquest into death" in pdf_text
    assert "{{" not in pdf_text


def test_generate_pdf_template_not_found_raises_error():
    """Test that requesting a non-existent template raises an error."""
    adapter = PdfGeneratorAdapter()

    with pytest.raises(TemplateNotFound):
        adapter.generate_pdf("nonexistent_template.html", {})


def test_generate_pdf_formats_cost_limitation_as_currency(certificate_pdf):
    """Test that cost_limitation is formatted as currency with thousands separator."""
    reader = PdfReader(BytesIO(certificate_pdf))
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    # Verify the cost limitation appears formatted as currency
    assert "£15,000" in pdf_text


def test_generate_print_letter_pdf_returns_valid_pdf(print_letter_pdf):
    """Test that generate_print_letter_pdf returns a valid PDF."""
    assert isinstance(print_letter_pdf, bytes)
    assert print_letter_pdf.startswith(b"%PDF")


def test_generate_print_letter_pdf_contains_cover_letter_content(print_letter_pdf):
    """Test that the combined PDF contains cover letter content."""
    reader = PdfReader(BytesIO(print_letter_pdf))
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "Civil Case Management" in pdf_text
    assert "Dear Jane Doe" in pdf_text
    assert "We issued your legal aid certificate" in pdf_text


def test_generate_print_letter_pdf_contains_certificate_content(print_letter_pdf):
    """Test that the combined PDF contains certificate content."""
    reader = PdfReader(BytesIO(print_letter_pdf))
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "Civil legal aid certificate" in pdf_text
    assert "Test Firm Ltd" in pdf_text


def test_generate_print_letter_pdf_contains_faq_content(print_letter_pdf):
    """Test that the combined PDF contains FAQ content."""
    reader = PdfReader(BytesIO(print_letter_pdf))
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "FAQs" in pdf_text
    assert "Important Information about your legal aid" in pdf_text
    assert "Statutory Charge" in pdf_text


def test_generate_print_letter_pdf_contains_cost_limitation_effective_date(
    print_letter_pdf,
):
    """Test that the combined PDF contains the cost_limitation_effective_date."""
    reader = PdfReader(BytesIO(print_letter_pdf))
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "15 July 1057" in pdf_text
    pdf_text_no_newlines = pdf_text.replace("\n", " ")
    assert "Cost limitation effective date" in pdf_text_no_newlines


def test_generate_print_letter_pdf_contains_end_date(
    print_letter_pdf,
):
    """Test that the combined PDF contains the end_date."""
    reader = PdfReader(BytesIO(print_letter_pdf))
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert pdf_text.count("15 July 2324") == 3
    pdf_text_no_newlines = pdf_text.replace("\n", " ")
    assert "End date" in pdf_text_no_newlines
