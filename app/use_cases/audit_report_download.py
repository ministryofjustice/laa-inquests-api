from app.models.audit.enums import AuditType
from app.ports.create_audit_event_port import AuditPort
from app.use_cases.exceptions import AuditError


class AuditReportDownloadUseCase:
    def __init__(self, audit_port: AuditPort) -> None:
        self.audit_port = audit_port

    def execute(
        self,
        user_email_address: str,
        report_type: AuditType,
        parameters: dict[str, str] | None = None,
    ) -> None:
        try:
            self.audit_port.audit_report_download(
                user_email_address=user_email_address,
                report_type=report_type,
                parameters=parameters,
            )
            self.audit_port.commit()
        except AuditError:
            self.audit_port.rollback()
            raise
