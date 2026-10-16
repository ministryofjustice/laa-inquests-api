from app.models.audit.index import ViewApplicationAudit
from app.ports.audit_port import AuditPort
from app.use_cases.exceptions import AuditError


class ViewApplicationAuditUseCase:
    def __init__(self, audit_port: AuditPort) -> None:
        self.audit_port = audit_port

    def execute(
        self,
        user_email_address: str,
        laa_reference: str,
        page: str,
    ) -> None:
        try:
            if user_email_address is None or user_email_address.strip() == "":
                raise ValueError(
                    "User email address must be provided for view application audit creation."
                )

            if laa_reference is None or laa_reference.strip() == "":
                raise ValueError(
                    "LAA reference must be provided for view application audit creation."
                )

            # TODO: Refactor so we have a use case for creating the audit event objects. Keep a single use case for committing the audit events to the db
            audit_event = ViewApplicationAudit(
                user_email_address=user_email_address,
                laa_reference=laa_reference,
                page=page,
            )
            self.audit_port.audit_event(audit_event)
            self.audit_port.commit()
        except AuditError:
            self.audit_port.rollback()
            raise
