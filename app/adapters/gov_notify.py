"""Gov Notify adapter for application emails."""

import logging
import time
from datetime import UTC, datetime
from io import BytesIO

from notifications_python_client import prepare_upload
from notifications_python_client.notifications import NotificationsAPIClient

from app.config import Config
from app.logging_utils import build_log_extra, duration_ms
from app.models.application.index import Application, ApplicationProceeding
from app.models.claim.index import Claim
from app.ports.gov_notify_port import GovNotifyPort
from app.use_cases.notify.create_application_grant_email_personalisation import (
    create_application_grant_email_personalisation,
)
from app.use_cases.notify.create_application_refusal_email_personalisation import (
    create_application_refusal_email_personalisation,
)
from app.use_cases.notify.create_application_submission_email_personalisation import (
    create_application_submission_email_personalisation,
)
from app.use_cases.notify.create_claim_rejection_email_personalisation import (
    create_claim_rejection_email_personalisation,
)
from app.use_cases.notify.create_claim_submission_email_personalisation import (
    create_claim_submission_email_personalisation,
)

logger = logging.getLogger(__name__)


class GovNotifyAdapter(GovNotifyPort):
    """Gov Notify adapter for application email notifications."""

    def __init__(self) -> None:
        self.client = NotificationsAPIClient(Config.GOV_NOTIFY_API_KEY)

    def _send_email_notification(
        self,
        *,
        template_id: str,
        personalisation: dict,
        event_name: str,
        email_address: str,
    ) -> None:
        started_at = time.perf_counter()
        try:
            self.client.send_email_notification(
                email_address=email_address,
                template_id=template_id,
                personalisation=personalisation,
            )
            logger.info(
                "GovNotify send success",
                extra=build_log_extra(
                    event=event_name,
                    route="govnotify:send_email_notification",
                    method="POST",
                    status_code=200,
                    duration_ms=duration_ms(started_at),
                    template_id=template_id,
                ),
            )
        except Exception as exc:
            logger.error(
                "GovNotify send failed",
                extra=build_log_extra(
                    event=f"{event_name}_failed",
                    route="govnotify:send_email_notification",
                    method="POST",
                    status_code=502,
                    duration_ms=duration_ms(started_at),
                    template_id=template_id,
                    exception_type=type(exc).__name__,
                ),
            )
            raise

    def send_application_refused_decision_email(
        self,
        application: Application,
        proceeding: ApplicationProceeding,
        recipient_email: str,
    ) -> None:
        personalisation = create_application_refusal_email_personalisation(
            application, proceeding
        )
        self._send_email_notification(
            email_address=recipient_email,
            template_id=Config.GOV_NOTIFY_APPLICATION_REFUSE_TEMPLATE_ID,
            personalisation=personalisation.model_dump(),
            event_name="govnotify_send_application_refused_decision_email",
        )

    def send_application_submit_confirmation_email(
        self, application: Application, recipient_email: str
    ) -> None:
        personalisation = create_application_submission_email_personalisation(
            application
        )
        self._send_email_notification(
            email_address=recipient_email,
            template_id=Config.GOV_NOTIFY_APPLICATION_SUBMIT_TEMPLATE_ID,
            personalisation=personalisation.model_dump(),
            event_name="govnotify_send_application_submit_confirmation_email",
        )

    def send_application_granted_decision_email(
        self,
        application: Application,
        proceeding: ApplicationProceeding,
        recipient_email: str,
        certificate_pdf: bytes,
    ) -> None:
        filename = f"{application.laa_reference}_Certificate_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.pdf"
        certificate_payload = prepare_upload(
            BytesIO(certificate_pdf), filename=filename
        )

        personalisation = create_application_grant_email_personalisation(
            application, proceeding, certificate_payload
        )
        self._send_email_notification(
            email_address=recipient_email,
            template_id=Config.GOV_NOTIFY_APPLICATION_GRANT_TEMPLATE_ID,
            personalisation=personalisation.model_dump(),
            event_name="govnotify_send_application_granted_decision_email",
        )

    def send_claim_submit_confirmation_email(
        self,
        claim: Claim,
        application: Application,
        recipient_email: str,
    ) -> None:
        personalisation = create_claim_submission_email_personalisation(
            claim,
            application,
        )
        self._send_email_notification(
            email_address=recipient_email,
            template_id=Config.GOV_NOTIFY_CLAIM_SUBMIT_TEMPLATE_ID,
            personalisation=personalisation.model_dump(),
            event_name="govnotify_send_claim_submit_confirmation_email",
        )

    def send_claim_rejected_decision_email(
        self,
        claim: Claim,
        application: Application,
        reject_reason: str,
        recipient_email: str,
        firm_name: str,
    ) -> None:
        personalisation = create_claim_rejection_email_personalisation(
            claim, application, reject_reason, firm_name
        )
        self.client.send_email_notification(
            email_address=recipient_email,
            template_id=Config.GOV_NOTIFY_CLAIM_REJECT_TEMPLATE_ID,
            personalisation=personalisation.model_dump(),
        )

    def send_precompiled_letter(self, reference: str, pdf: bytes) -> None:
        started_at = time.perf_counter()
        try:
            self.client.send_precompiled_letter_notification(
                reference=f"{reference}-{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
                pdf_file=BytesIO(pdf),
            )
            logger.info(
                "GovNotify send success",
                extra=build_log_extra(
                    event="govnotify_send_precompiled_letter",
                    route="govnotify:send_precompiled_letter_notification",
                    method="POST",
                    status_code=200,
                    duration_ms=duration_ms(started_at),
                ),
            )
        except Exception as exc:
            logger.error(
                "GovNotify send failed",
                extra=build_log_extra(
                    event="govnotify_send_precompiled_letter_failed",
                    route="govnotify:send_precompiled_letter_notification",
                    method="POST",
                    status_code=502,
                    duration_ms=duration_ms(started_at),
                    exception_type=type(exc).__name__,
                ),
            )
            raise
