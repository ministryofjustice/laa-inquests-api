from enum import StrEnum


class AuditType(StrEnum):
    NOT_AUDITABLE = "Not Auditable"

    REPORTS_CLAIMS_BACKLOG = "Claims Backlog"
    REPORTS_APPLICATIONS_BACKLOG = "Applications Backlog"
    REPORTS_PAYMENT_EXTRACT = "Payment Extract"
