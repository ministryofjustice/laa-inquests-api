from fastapi import Request
from fastapi.concurrency import run_in_threadpool

from app.use_cases.audit.view_application_audit import ViewApplicationAuditUseCase


class ViewApplicationAuditWriter:
    """Records a view application audit event for a specific page."""

    def __init__(
        self,
        page: str,
    ) -> None:
        self.page = page

    async def __call__(
        self,
        user_email_address: str,
        use_case: ViewApplicationAuditUseCase,
        request: Request,
    ) -> None:
        # The use case performs blocking database I/O, so keep it off the event loop.
        await run_in_threadpool(
            use_case.execute,
            user_email_address=user_email_address,
            laa_reference=request.path_params["laa_reference"],
            page=self.page,
        )
