import logging

from app.logging_utils import build_log_extra
from app.models.application.certificate import ApplicationCertificate
from app.models.application.index import Application, ApplicationProceeding
from app.ports.gov_notify_port import GovNotifyPort
from app.ports.pdf_generation_port import PdfGenerationPort

logger = logging.getLogger(__name__)


class SendGrantEmailUseCase:
    def __init__(
        self,
        pdf_generation_port: PdfGenerationPort,
        gov_notify_port: GovNotifyPort,
    ) -> None:
        self.pdf_generation_port = pdf_generation_port
        self.gov_notify_port = gov_notify_port

    def execute(
        self,
        application: Application,
        proceeding: ApplicationProceeding,
        certificate_context: ApplicationCertificate,
    ) -> None:
        try:
            certificate_pdf = self.pdf_generation_port.generate_pdf(
                "certificate.html", certificate_context
            )

            self.gov_notify_port.send_application_granted_decision_email(
                application,
                proceeding,
                application.provider.email_address,
                certificate_pdf,
            )
            logger.info(
                "Grant email sent",
                extra=build_log_extra(
                    event="grant_email_sent",
                    laa_reference=application.laa_reference,
                ),
            )
        except Exception:
            logger.error(
                "Grant email send failed",
                extra=build_log_extra(
                    event="grant_email_send_failed",
                    laa_reference=application.laa_reference,
                ),
                exc_info=True,
            )
            raise
