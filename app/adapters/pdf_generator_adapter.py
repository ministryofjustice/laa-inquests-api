"""WeasyPrint adapter for PDF generation."""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from app.ports.pdf_generation_port import PdfGenerationPort


class PdfGeneratorAdapter(PdfGenerationPort):
    """WeasyPrint adapter for generating PDFs from HTML templates."""

    def __init__(self) -> None:
        # Set up Jinja2 environment to load templates from app/templates/
        self._template_dir = Path(__file__).parent.parent / "templates"
        self.jinja_env = Environment(loader=FileSystemLoader(str(self._template_dir)))

    def generate_pdf(self, template_name: str, context: dict) -> bytes:
        """
        Generate a PDF from an HTML template with FAQs page automatically appended.

        Args:
            template_name: Name of the template file (e.g., 'certificate.html')
            context: Dictionary of variables to pass to the template

        Returns:
            PDF content as bytes
        """
        # Render the main template with the provided context
        template = self.jinja_env.get_template(template_name)
        html_content = template.render(**context)

        template_path = self._template_dir / template_name
        pdf_bytes = HTML(string=html_content, base_url=str(template_path)).write_pdf()

        return pdf_bytes
