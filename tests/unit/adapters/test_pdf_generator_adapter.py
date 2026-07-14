"""Unit tests for WeasyPrint adapter."""

import pytest

from app.adapters.pdf_generator_adapter import PdfGeneratorAdapter


def test_generate_pdf_returns_bytes():
    """Test that generate_pdf returns bytes."""
    adapter = PdfGeneratorAdapter()
    context = {"header_text": "Test Header"}

    result = adapter.generate_pdf("govuk_header.html", context)

    assert isinstance(result, bytes)
    assert len(result) > 0


def test_generate_pdf_returns_valid_pdf():
    """Test that generate_pdf returns content starting with PDF magic bytes."""
    adapter = PdfGeneratorAdapter()
    context = {"header_text": "Test Header"}

    result = adapter.generate_pdf("govuk_header.html", context)

    # PDF files start with %PDF
    assert result.startswith(b"%PDF")


def test_generate_pdf_with_different_context_values():
    """Test that different context values produce different PDFs."""
    adapter = PdfGeneratorAdapter()

    pdf1 = adapter.generate_pdf("govuk_header.html", {"header_text": "Header 1"})
    pdf2 = adapter.generate_pdf("govuk_header.html", {"header_text": "Header 2"})

    # Different context should produce different PDFs
    assert pdf1 != pdf2


def test_generate_pdf_template_not_found_raises_error():
    """Test that requesting a non-existent template raises an error."""
    adapter = PdfGeneratorAdapter()

    with pytest.raises(Exception):  # Jinja2 will raise TemplateNotFound
        adapter.generate_pdf("nonexistent_template.html", {})
