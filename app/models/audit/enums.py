from enum import StrEnum


class ReportType(StrEnum):
    CLAIMS_BACKLOG = "Claims Backlog"
    APPLICATIONS_BACKLOG = "Applications Backlog"
    PAYMENT_EXTRACT = "Payment Extract"
    AUDIT_TRAIL = "User Audit Trail"


class AuditEventReference(StrEnum):
    """Case Audit event references from the Event Catalogue (EVT-AUD-###)."""

    APPLICATION_VIEWED = "EVT-AUD-001"
    REPORT_DOWNLOADED = "EVT-AUD-002"
    CERTIFICATE_VIEWED = "EVT-AUD-003"


class ApplicationPageType(StrEnum):
    OVERVIEW = "overview"
    CERTIFICATE = "certificate"
