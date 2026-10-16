from fastapi import Request
from fastapi.concurrency import run_in_threadpool

from app.models.audit.enums import ReportType
from app.use_cases.audit.report_audit import ReportAuditUseCase


class ReportAuditWriter:
    """Records a report audit event for a specific report type."""

    def __init__(
        self,
        report_type: ReportType,
    ) -> None:
        self.report_type = report_type

    async def __call__(
        self,
        user_email_address: str,
        use_case: ReportAuditUseCase,
        request: Request,
    ) -> None:
        # The use case performs blocking database I/O, so keep it off the event loop.
        await run_in_threadpool(
            use_case.execute,
            user_email_address=user_email_address,
            report_type=self.report_type,
            # Only the payment extract is filtered by user-supplied query parameters.
            parameters=dict(request.query_params)
            if self.report_type == ReportType.PAYMENT_EXTRACT
            else None,
        )
