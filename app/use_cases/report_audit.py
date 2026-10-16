from app.models.audit.enums import ReportType
from app.models.audit.index import ReportAudit
from app.ports.audit_port import AuditPort
from app.use_cases.exceptions import AuditError


class ReportAuditUseCase:
    def __init__(self, audit_port: AuditPort) -> None:
        self.audit_port = audit_port

    def execute(
        self,
        user_email_address: str,
        report_type: ReportType,
        parameters: dict[str, str] | None = None,
    ) -> None:
        try:
            if user_email_address is None or user_email_address.strip() == "":
                raise ValueError(
                    "User email address must be provided for report audit creation."
                )
            audit_event = ReportAudit(
                user_email_address=user_email_address,
                report_type=report_type,
                parameters=parameters,
            )
            self.audit_port.audit_event(audit_event)
            self.audit_port.commit()
        except AuditError:
            self.audit_port.rollback()
            raise
