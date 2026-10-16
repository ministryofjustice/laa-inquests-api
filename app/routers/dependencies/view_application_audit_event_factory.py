from fastapi import Request

from app.models.audit.index import BaseAuditEvent, ViewApplicationAudit


class ViewApplicationAuditEventFactory:
    """Builds the audit event for viewing a specific page of an application."""

    def __init__(self, page: str) -> None:
        self.page = page

    def __call__(self, user_email_address: str, request: Request) -> BaseAuditEvent:
        return ViewApplicationAudit(
            user_email_address=user_email_address,
            laa_reference=request.path_params["laa_reference"],
            page=self.page,
        )
