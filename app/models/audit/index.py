from datetime import UTC, datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.audit.enums import ApplicationPageType, ReportType


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


class ViewApplicationPagesAudit(BaseAuditEvent, table=True):
    __tablename__ = "view_application_pages_audit_event"

    laa_reference: str = Field(nullable=False)
    page: ApplicationPageType = Field(nullable=False)
