from datetime import UTC, datetime

from app.models.audit.enums import ReportType
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class BaseAuditEvent(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(
        nullable=False, default_factory=lambda: datetime.now(UTC)
    )
    user_email_address: str = Field(nullable=False)


class ReportDownloadAudit(BaseAuditEvent, table=True):
    __tablename__ = "audit_report_download_event"

    report_type: ReportType = Field(nullable=False)
    parameters: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
