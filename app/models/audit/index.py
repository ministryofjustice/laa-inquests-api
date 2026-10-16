from datetime import UTC, datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.audit.enums import ReportType


class BaseAuditEvent(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(
        nullable=False, default_factory=lambda: datetime.now(UTC)
    )
    user_email_address: str = Field(nullable=False)


class ReportAudit(BaseAuditEvent, table=True):
    __tablename__ = "report_audit_event"

    report_type: ReportType = Field(nullable=False)
    parameters: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))


class ViewApplicationAudit(BaseAuditEvent, table=True):
    __tablename__ = "view_application_audit_event"

    laa_reference: str = Field(nullable=False)
    page: str = Field(
        nullable=False
    )  # TODO currently hardcode for getapplication, consider certificates, create a new enum for age type
