from fastapi import Request

from app.models.audit.enums import ReportType
from app.models.audit.index import BaseAuditEvent, ReportAudit

_REPORT_TYPES_WITH_PARAMETERS = {
    ReportType.PAYMENT_EXTRACT,
    ReportType.AUDIT_TRAIL,
    ReportType.DECISIONS,
}


class ReportAuditEventFactory:
    """Builds the audit event for a report download of a specific report type."""

    def __init__(self, report_type: ReportType) -> None:
        self.report_type = report_type

    def __call__(self, user_email_address: str, request: Request) -> BaseAuditEvent:
        return ReportAudit(
            user_email_address=user_email_address,
            report_type=self.report_type,
            # Only date-range reports are filtered by user-supplied query parameters.
            parameters=dict(request.query_params)
            if self.report_type in _REPORT_TYPES_WITH_PARAMETERS
            else None,
        )
