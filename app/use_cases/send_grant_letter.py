"""Use case for sending grant letter print pack via Gov Notify precompiled letter."""

import logging

from app.logging_utils import build_log_extra
from app.models.application.certificate import ApplicationCertificate
from app.ports.gov_notify_port import GovNotifyPort
from app.ports.pdf_generation_port import PdfGenerationPort

logger = logging.getLogger(__name__)


class SendGrantLetterUseCase:
    def __init__(
        self,
        pdf_generation_port: PdfGenerationPort,
        gov_notify_port: GovNotifyPort,
    ) -> None:
        self.pdf_generation_port = pdf_generation_port
        self.gov_notify_port = gov_notify_port

    def execute(self, certificate_context: ApplicationCertificate) -> None:
        try:
            print_letter_pdf = self.pdf_generation_port.generate_print_letter_pdf(
                certificate_context
            )

            self.gov_notify_port.send_precompiled_letter(
                str(certificate_context.laa_reference),
                print_letter_pdf,
            )
            logger.info(
                "Grant letter sent",
                extra=build_log_extra(
                    event="grant_letter_sent",
                    laa_reference=certificate_context.laa_reference,
                ),
            )
        except Exception:
            logger.warning(
                "Grant letter send failed",
                extra=build_log_extra(
                    event="grant_letter_send_failed",
                    laa_reference=certificate_context.laa_reference,
                ),
                exc_info=True,
            )
            raise
