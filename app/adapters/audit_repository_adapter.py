import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.logging_utils import build_log_extra
from app.models.audit.index import BaseAuditEvent
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
        event = adapter.audit_event(
            audit_event=ReportAudit(
                user_email_address="user@example.com",
                report_type=ReportType.CLAIMS_BACKLOG,
                parameters={"from_date": "2024-01-01", "to_date": "2024-01-31"},
            )
        )
        adapter.commit()
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # def audit_report(
    #     self,
    #     user_email_address: str,
    #     report_type: ReportType,
    #     parameters: dict | None = None,
    # ) -> ReportAudit:
    #     """
    #     Create a new report audit record.

    #     Args:
    #         user_email_address: Email address of the user that triggered the report download
    #         report_type: Type of the report being downloaded
    #         parameters: Optional JSON data associated with the report
    #             (e.g., {"from_date": "2024-01-01", "to_date": "2024-01-31"})

    #     Returns:
    #         The created ReportAudit with auto-generated id and timestamp
    #     """
    #     if user_email_address is None or user_email_address.strip() == "":
    #         raise ValueError(
    #             "User email address must be provided for report audit creation."
    #         )

    #     audit_event = ReportAudit(
    #         user_email_address=user_email_address,
    #         report_type=report_type,
    #         parameters=parameters,
    #     )
    #     try:
    #         self.session.add(audit_event)
    #         self.session.flush()
    #         self.session.refresh(audit_event)
    #     except SQLAlchemyError as exc:
    #         raise AuditError("Failed to write report audit") from exc
    #     logger.info(
    #         "Report download audit created",
    #         extra=build_log_extra(
    #             event="report_audit_created",
    #             report_audit_id=audit_event.id,
    #         ),
    #     )
    #     return audit_event

    def audit_event(self, audit_event: BaseAuditEvent) -> BaseAuditEvent:
        """
        Create a new audit record.

        Args:
            audit_event: The audit event to be recorded

        Returns:
            The created audit event with auto-generated id and timestamp
        """
        try:
            self.session.add(audit_event)
            self.session.flush()
            self.session.refresh(audit_event)
        except SQLAlchemyError as exc:
            raise AuditError("Failed to write audit event") from exc
        logger.info(
            "Audit event created",
            extra=build_log_extra(
                event="audit_event_created",
                audit_event_id=audit_event.id,
            ),
        )
        return audit_event

    def commit(self) -> None:
        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            raise AuditError("Failed to commit audit event") from exc

    def rollback(self) -> None:
        try:
            self.session.rollback()
        except SQLAlchemyError as exc:
            raise AuditError("Failed to roll back audit event") from exc
