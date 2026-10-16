from enum import StrEnum


class ReportType(StrEnum):
    CLAIMS_BACKLOG = "Claims Backlog"
    APPLICATIONS_BACKLOG = "Applications Backlog"
    PAYMENT_EXTRACT = "Payment Extract"


class ApplicationPageType(StrEnum):
    OVERVIEW = "overview"
    CERTIFICATE = "certificate"
