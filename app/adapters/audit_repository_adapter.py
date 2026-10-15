import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.logging_utils import build_log_extra
from app.models.audit.enums import ReportType
from app.models.audit.index import ReportAudit
from app.ports.audit_port import AuditPort
from app.use_cases.exceptions import AuditError

logger = logging.getLogger(__name__)


class AuditRepositoryAdapter(AuditPort):
    """
    Adapter for creating and persisting audit events to the database.

    This adapter implements the AuditPort and provides transaction
    support via commit() and rollback() methods.

    Example usage:
        adapter = AuditRepositoryAdapter(session)
        event = adapter.audit_report(
            user_email_address="user@example.com",
            report_type=ReportType.CLAIMS_BACKLOG,
        )
        adapter.commit()
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def audit_report(
        self,
        user_email_address: str,
        report_type: ReportType,
        parameters: dict | None = None,
    ) -> ReportAudit:
        """
        Create a new report audit record.

        Args:
            user_email_address: Email address of the user that triggered the report download
            report_type: Type of the report being downloaded
            parameters: Optional JSON data associated with the report
                (e.g., {"from_date": "2024-01-01", "to_date": "2024-01-31"})

        Returns:
            The created ReportAudit with auto-generated id and timestamp
        """
        if user_email_address is None or user_email_address.strip() == "":
            raise ValueError(
                "User email address must be provided for report audit creation."
            )

        new_event = ReportAudit(
            user_email_address=user_email_address,
            report_type=report_type,
            parameters=parameters,
        )
        try:
            self.session.add(new_event)
            self.session.flush()
            self.session.refresh(new_event)
        except SQLAlchemyError as exc:
            raise AuditError("Failed to write report audit") from exc
        logger.info(
            "Report download audit created",
            extra=build_log_extra(
                event="report_audit_created",
                report_audit_id=new_event.id,
            ),
        )
        return new_event

    def commit(self) -> None:
        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            raise AuditError("Failed to commit report audit") from exc

    def rollback(self) -> None:
        try:
            self.session.rollback()
        except SQLAlchemyError as exc:
            raise AuditError("Failed to roll back report audit") from exc
