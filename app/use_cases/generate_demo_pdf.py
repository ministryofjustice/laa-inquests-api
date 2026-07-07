from app.ports.pdf_generation_port import PdfGenerationPort


class GenerateDemoPdfUseCase:
    def __init__(self, pdf_generation_port: PdfGenerationPort) -> None:
        self.pdf_generation_port = pdf_generation_port

    def execute(self) -> bytes:
        """Generate a demo PDF with a GOV.UK header and FAQs page."""
        context = {"header_text": "Example GOV.UK Header"}
        return self.pdf_generation_port.generate_pdf("govuk_header_demo.html", context)
