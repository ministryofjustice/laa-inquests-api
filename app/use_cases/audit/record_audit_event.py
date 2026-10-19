from app.models.audit.index import BaseAuditEvent
from app.ports.audit_port import AuditPort
from app.use_cases.exceptions import AuditError


class RecordAuditEventUseCase:
    def __init__(self, audit_port: AuditPort) -> None:
        self.audit_port = audit_port

    def execute(self, audit_event: BaseAuditEvent) -> None:
        try:
            if (
                audit_event.user_email_address is None
                or audit_event.user_email_address.strip() == ""
            ):
                raise ValueError(
                    "User email address must be provided for audit creation."
                )
            self.audit_port.audit_event(audit_event)
            self.audit_port.commit()
        except AuditError:
            self.audit_port.rollback()
            raise
