"""Unit tests for WeasyPrint adapter."""

import pytest

from app.adapters.weasyprint_adapter import WeasyPrintAdapter


def test_generate_pdf_returns_bytes():
    """Test that generate_pdf returns bytes."""
    adapter = WeasyPrintAdapter()
    context = {"header_text": "Test Header"}

    result = adapter.generate_pdf("govuk_header_demo.html", context)

    assert isinstance(result, bytes)
    assert len(result) > 0


def test_generate_pdf_returns_valid_pdf():
    """Test that generate_pdf returns content starting with PDF magic bytes."""
    adapter = WeasyPrintAdapter()
    context = {"header_text": "Test Header"}

    result = adapter.generate_pdf("govuk_header_demo.html", context)

    # PDF files start with %PDF
    assert result.startswith(b"%PDF")


def test_generate_pdf_includes_faqs_page():
    """Test that generate_pdf automatically appends FAQs page."""
    adapter = WeasyPrintAdapter()
    context = {"header_text": "Test Header"}

    result = adapter.generate_pdf("govuk_header_demo.html", context)

    # Multi-page PDF with FAQs should be larger than minimal single page
    # TODO: Better assertions of PDF content
    assert len(result) > 5000


def test_generate_pdf_with_different_context_values():
    """Test that different context values produce different PDFs."""
    adapter = WeasyPrintAdapter()

    pdf1 = adapter.generate_pdf("govuk_header_demo.html", {"header_text": "Header 1"})
    pdf2 = adapter.generate_pdf("govuk_header_demo.html", {"header_text": "Header 2"})

    # Different context should produce different PDFs
    assert pdf1 != pdf2


def test_generate_pdf_template_not_found_raises_error():
    """Test that requesting a non-existent template raises an error."""
    adapter = WeasyPrintAdapter()

    with pytest.raises(Exception):  # Jinja2 will raise TemplateNotFound
        adapter.generate_pdf("nonexistent_template.html", {})
