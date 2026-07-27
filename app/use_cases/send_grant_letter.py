"""Use case for sending grant letter print pack via Gov Notify precompiled letter."""

from app.models.application.certificate import ApplicationCertificate
from app.ports.gov_notify_port import GovNotifyPort
from app.ports.pdf_generation_port import PdfGenerationPort


class SendGrantLetterUseCase:
    def __init__(
        self,
        pdf_generation_port: PdfGenerationPort,
        gov_notify_port: GovNotifyPort,
    ) -> None:
        self.pdf_generation_port = pdf_generation_port
        self.gov_notify_port = gov_notify_port

    def execute(self, certificate_context: ApplicationCertificate) -> None:
        print_letter_pdf = self.pdf_generation_port.generate_print_letter_pdf(
            certificate_context
        )

        self.gov_notify_port.send_precompiled_letter(
            str(certificate_context.laa_reference),
            print_letter_pdf,
        )
