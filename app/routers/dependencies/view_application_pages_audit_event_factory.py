from fastapi import Request

from app.models.audit.enums import ApplicationPageType
from app.models.audit.index import BaseAuditEvent, ViewApplicationPagesAudit


class ViewApplicationPagesAuditEventFactory:
    """Builds the audit event for viewing a specific page of an application."""

    def __init__(self, page: ApplicationPageType) -> None:
        self.page = page

    def __call__(self, user_email_address: str, request: Request) -> BaseAuditEvent:
        return ViewApplicationPagesAudit(
            user_email_address=user_email_address,
            laa_reference=request.path_params["laa_reference"],
            page=self.page,
        )
