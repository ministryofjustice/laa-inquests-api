"""WeasyPrint adapter for PDF generation."""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.ports.pdf_generation_port import PdfGenerationPort


class WeasyPrintAdapter(PdfGenerationPort):
    """WeasyPrint adapter for generating PDFs from HTML templates."""

    def __init__(self) -> None:
        # Set up Jinja2 environment to load templates from app/templates/
        template_dir = Path(__file__).parent.parent / "templates"
        self.jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate_pdf(self, template_name: str, context: dict) -> bytes:
        """
        Generate a PDF from an HTML template with FAQs page automatically appended.

        Args:
            template_name: Name of the template file (e.g., 'govuk_header_demo.html')
            context: Dictionary of variables to pass to the template

        Returns:
            PDF content as bytes
        """
        # Render the main template with the provided context
        template = self.jinja_env.get_template(template_name)
        html_content = template.render(**context)

        # Render the FAQs template (no context needed)
        faqs_template = self.jinja_env.get_template("govuk_faqs.html")
        faqs_html = faqs_template.render()

        # Combine main content and FAQs with page break
        page_break = '<div style="page-break-before: always;"></div>'
        combined_html = html_content + page_break + faqs_html

        # Convert combined HTML to PDF using WeasyPrint
        pdf_bytes = HTML(string=combined_html).write_pdf()

        return pdf_bytes
