from collections.abc import Iterator
from datetime import datetime

from sqlmodel import Session, select

from app.domain.audit_trail import (
    AuditTrailEvent,
    application_certificate_view_event,
    application_overview_view_event,
    history_event,
    report_download_event,
)
from app.models.application.index import Application, Provider
from app.models.audit.enums import ApplicationPageType
from app.models.audit.index import ReportAudit, ViewApplicationPagesAudit
from app.models.history.index import HistoryEvent
from app.ports.audit_trail_report_port import AuditTrailReportPort

BATCH_SIZE = 500


class AuditTrailRepositoryAdapter(AuditTrailReportPort):
    def __init__(self, session: Session) -> None:
        self.session = session

    def iter_history_events(
        self, from_inclusive: datetime, before_exclusive: datetime
    ) -> Iterator[AuditTrailEvent]:
        statement = (
            select(
                HistoryEvent,
                Application.laa_reference,
                Provider.firm_code,
                Provider.office_id,
            )
            .join(
                Application, HistoryEvent.application_id == Application.application_id
            )
            .join(Provider, Application.provider_id == Provider.provider_id)
            .where(
                HistoryEvent.timestamp >= from_inclusive,
                HistoryEvent.timestamp < before_exclusive,
            )
            .order_by(HistoryEvent.timestamp, HistoryEvent.id)
            .execution_options(yield_per=BATCH_SIZE)
        )
        for event, laa_reference, firm_code, office_id in self.session.exec(statement):
            yield history_event(
                occurred_at=event.timestamp,
                event_reference=event.event_reference.value,
                actor_type=event.actor_type,
                actor=event.actor,
                actor_email_address=event.actor_email_address,
                laa_reference=laa_reference,
                firm_code=firm_code,
                office_id=office_id,
                event_data=event.event_data,
            )

    def iter_application_view_events(
        self, from_inclusive: datetime, before_exclusive: datetime
    ) -> Iterator[AuditTrailEvent]:
        statement = (
            select(ViewApplicationPagesAudit)
            .where(
                ViewApplicationPagesAudit.timestamp >= from_inclusive,
                ViewApplicationPagesAudit.timestamp < before_exclusive,
            )
            .order_by(ViewApplicationPagesAudit.timestamp, ViewApplicationPagesAudit.id)
            .execution_options(yield_per=BATCH_SIZE)
        )
        for event in self.session.exec(statement):
            yield self._view_event(event)

    @staticmethod
    def _view_event(event: ViewApplicationPagesAudit) -> AuditTrailEvent:
        match event.page:
            case ApplicationPageType.OVERVIEW:
                to_domain_event = application_overview_view_event
            case ApplicationPageType.CERTIFICATE:
                to_domain_event = application_certificate_view_event
        return to_domain_event(
            occurred_at=event.timestamp,
            user_email_address=event.user_email_address,
            laa_reference=event.laa_reference,
        )

    def iter_report_events(
        self, from_inclusive: datetime, before_exclusive: datetime
    ) -> Iterator[AuditTrailEvent]:
        statement = (
            select(ReportAudit)
            .where(
                ReportAudit.timestamp >= from_inclusive,
                ReportAudit.timestamp < before_exclusive,
            )
            .order_by(ReportAudit.timestamp, ReportAudit.id)
            .execution_options(yield_per=BATCH_SIZE)
        )
        for event in self.session.exec(statement):
            yield report_download_event(
                occurred_at=event.timestamp,
                user_email_address=event.user_email_address,
                report_type=event.report_type,
            )
