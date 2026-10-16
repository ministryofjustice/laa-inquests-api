from fastapi import Request

from app.models.audit.enums import ReportType
from app.models.audit.index import BaseAuditEvent, ReportAudit


class ReportAuditEventFactory:
    """Builds the audit event for a report download of a specific report type."""

    def __init__(self, report_type: ReportType) -> None:
        self.report_type = report_type

    def __call__(self, user_email_address: str, request: Request) -> BaseAuditEvent:
        return ReportAudit(
            user_email_address=user_email_address,
            report_type=self.report_type,
            # Only the payment extract is filtered by user-supplied query parameters.
            parameters=dict(request.query_params)
            if self.report_type == ReportType.PAYMENT_EXTRACT
            else None,
        )
