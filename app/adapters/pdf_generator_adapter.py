"""WeasyPrint adapter for PDF generation."""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from app.ports.pdf_generation_port import PdfGenerationPort
from app.models.application.certificate import ApplicationCertificate


class PdfGeneratorAdapter(PdfGenerationPort):
    """WeasyPrint adapter for generating PDFs from HTML templates."""

    def __init__(self) -> None:
        self._template_dir = Path(__file__).parent.parent / "templates"
        self.jinja_env = Environment(loader=FileSystemLoader(str(self._template_dir)))

    def generate_pdf(
        self, template_name: str, context: ApplicationCertificate
    ) -> bytes:
        """
        Generate a PDF from an HTML template with FAQs page automatically appended.

        Args:
            template_name: Name of the template file (e.g., 'certificate.html')
            context: Dictionary of variables to pass to the template

        Returns:
            PDF content as bytes
        """
        template = self.jinja_env.get_template(template_name)
        html_content = template.render(**context.model_dump())

        template_path = self._template_dir / template_name
        pdf_bytes = HTML(string=html_content, base_url=str(template_path)).write_pdf()

        return pdf_bytes

    def generate_print_letter_pdf(self, context: ApplicationCertificate) -> bytes:
        """Generate a combined print-ready PDF with cover letter, certificate, and FAQ."""

        template_names = ["cover_letter.html", "certificate.html", "faq.html"]
        context_data = context.model_dump()

        html_sections = []
        for template_name in template_names:
            template = self.jinja_env.get_template(template_name)
            html_sections.append(template.render(**context_data))

        # Build combined HTML with page breaks between sections
        parts = []
        for i, section in enumerate(html_sections):
            if i > 0:
                parts.append('<div style="page-break-before: always;"></div>')
            parts.append(section)
        combined_html = "\n".join(parts)

        base_url = str(self._template_dir / "cover_letter.html")
        pdf_bytes = HTML(string=combined_html, base_url=base_url).write_pdf()

        return pdf_bytes
