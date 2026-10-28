import logging
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.adapters.application_repository_adapter import ApplicationRepositoryAdapter
from app.adapters.audit_trail_repository_adapter import AuditTrailRepositoryAdapter
from app.adapters.claim_repository_adapter import ClaimRepositoryAdapter
from app.auth.rbac import Permission
from app.db import get_session
from app.logging_utils import build_log_extra
from app.models.audit.enums import ReportType
from app.ports.application_backlog_port import ApplicationBacklogPort
from app.ports.audit_trail_report_port import AuditTrailReportPort
from app.ports.claim.payment_extract_report_port import PaymentExtractReportPort
from app.ports.claim_backlog_port import ClaimBacklogPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.routers.applications import get_provider_details_port
from app.routers.dependencies.auditer_permission_checker import (
    audit_and_require_permission,
)
from app.routers.dependencies.report_audit_event_factory import (
    ReportAuditEventFactory,
)
from app.use_cases.exceptions import (
    InvalidDateRangeError,
    ProviderDetailsRetrievalError,
    ReportGenerationError,
)
from app.use_cases.generate_application_backlog_report import (
    GenerateApplicationBacklogReportUseCase,
)
from app.use_cases.generate_audit_trail_report import (
    GenerateAuditTrailReportUseCase,
)
from app.use_cases.generate_claim_backlog_report import (
    GenerateClaimBacklogReportUseCase,
)
from app.use_cases.generate_payment_extract_report import (
    GeneratePaymentExtractReportUseCase,
)

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)

logger = logging.getLogger(__name__)


def _route(request: Request | None) -> str | None:
    return request.url.path if request is not None else None


def _method(request: Request | None) -> str | None:
    return request.method if request is not None else None


def get_application_backlog_port(
    session: Session = Depends(get_session),
) -> ApplicationBacklogPort:
    return ApplicationRepositoryAdapter(session=session)


def get_generate_application_backlog_report_use_case(
    application_backlog_port: ApplicationBacklogPort = Depends(
        get_application_backlog_port
    ),
    provider_details_port: ProviderDetailsPort = Depends(get_provider_details_port),
) -> GenerateApplicationBacklogReportUseCase:
    return GenerateApplicationBacklogReportUseCase(
        application_backlog_port=application_backlog_port,
        provider_details_port=provider_details_port,
    )


def get_claim_backlog_port(
    session: Session = Depends(get_session),
) -> ClaimBacklogPort:
    return ClaimRepositoryAdapter(session=session)


def get_generate_claim_backlog_report_use_case(
    claim_backlog_port: ClaimBacklogPort = Depends(get_claim_backlog_port),
    provider_details_port: ProviderDetailsPort = Depends(get_provider_details_port),
) -> GenerateClaimBacklogReportUseCase:
    return GenerateClaimBacklogReportUseCase(
        claim_backlog_port=claim_backlog_port,
        provider_details_port=provider_details_port,
    )


def get_payment_extract_report_port(
    session: Session = Depends(get_session),
) -> PaymentExtractReportPort:
    return ClaimRepositoryAdapter(session=session)


def get_generate_payment_extract_report_use_case(
    payment_extract_report_port: PaymentExtractReportPort = Depends(
        get_payment_extract_report_port
    ),
    provider_details_port: ProviderDetailsPort = Depends(get_provider_details_port),
) -> GeneratePaymentExtractReportUseCase:
    return GeneratePaymentExtractReportUseCase(
        payment_extract_report_port=payment_extract_report_port,
        provider_details_port=provider_details_port,
    )


def get_audit_trail_report_port(
    session: Session = Depends(get_session),
) -> AuditTrailReportPort:
    return AuditTrailRepositoryAdapter(session=session)


def get_generate_audit_trail_report_use_case(
    audit_trail_report_port: AuditTrailReportPort = Depends(
        get_audit_trail_report_port
    ),
    provider_details_port: ProviderDetailsPort = Depends(get_provider_details_port),
) -> GenerateAuditTrailReportUseCase:
    return GenerateAuditTrailReportUseCase(
        audit_trail_report_port=audit_trail_report_port,
        provider_details_port=provider_details_port,
    )


@router.get(
    "/applications/backlog",
    dependencies=[
        Depends(
            audit_and_require_permission(
                possible_permissions=Permission.REPORTS_APPLICATION_WORKFLOW_READ,
                audit_event_factory=ReportAuditEventFactory(
                    report_type=ReportType.APPLICATIONS_BACKLOG
                ),
            )
        ),
    ],
)
def get_application_backlog_report(
    use_case: GenerateApplicationBacklogReportUseCase = Depends(
        get_generate_application_backlog_report_use_case
    ),
    request: Request = None,
) -> StreamingResponse:
    """Generate a CSV report of all open application cases pending assessment or decision."""
    try:
        csv_content = use_case.execute()
    except (ReportGenerationError, ProviderDetailsRetrievalError) as exc:
        logger.error(
            "Application backlog report generation failed",
            extra=build_log_extra(
                event="application_backlog_report_failed",
                route=_route(request),
                method=_method(request),
                status_code=500,
                error_type=type(exc).__name__,
            ),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate application backlog report: {exc}",
        )

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=application_backlog_report.csv"
        },
    )


@router.get(
    "/claims/backlog",
    dependencies=[
        Depends(
            audit_and_require_permission(
                possible_permissions=Permission.REPORTS_CLAIM_WORKFLOW_READ,
                audit_event_factory=ReportAuditEventFactory(
                    report_type=ReportType.CLAIMS_BACKLOG
                ),
            )
        ),
    ],
)
def get_claim_backlog_report(
    use_case: GenerateClaimBacklogReportUseCase = Depends(
        get_generate_claim_backlog_report_use_case
    ),
    request: Request = None,
) -> StreamingResponse:
    """Generate a CSV report of all open claims pending assessment or decision."""
    try:
        csv_content = use_case.execute()
    except (ReportGenerationError, ProviderDetailsRetrievalError) as exc:
        logger.error(
            "Claim backlog report generation failed",
            extra=build_log_extra(
                event="claim_backlog_report_failed",
                route=_route(request),
                method=_method(request),
                status_code=500,
                error_type=type(exc).__name__,
            ),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate claim backlog report: {exc}",
        )

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=claims_backlog_report.csv"
        },
    )


@router.get(
    "/payment-extract",
    dependencies=[
        Depends(
            audit_and_require_permission(
                possible_permissions=Permission.REPORTS_PAYMENT_READ,
                audit_event_factory=ReportAuditEventFactory(
                    report_type=ReportType.PAYMENT_EXTRACT
                ),
            )
        ),
    ],
)
def get_payment_extract_report(
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
    use_case: GeneratePaymentExtractReportUseCase = Depends(
        get_generate_payment_extract_report_use_case
    ),
    request: Request = None,
) -> StreamingResponse:
    """Stream a CSV of payment extract lines created between two dates (inclusive)."""

    try:
        chunks = use_case.execute(from_date, to_date)
    except InvalidDateRangeError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid date range: {exc}",
        )
    except (
        ReportGenerationError,
        ProviderDetailsRetrievalError,
        SQLAlchemyError,
    ) as exc:
        logger.error(
            "Payment extract report generation failed",
            extra=build_log_extra(
                event="payment_extract_report_failed",
                route=_route(request),
                method=_method(request),
                status_code=500,
                error_type=type(exc).__name__,
            ),
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to generate payment extract report",
        )
    filename = f"{datetime.now(UTC).strftime('%Y-%m-%d-%H%M%S')} - Report - IDDS Financial Payments - OFFICIAL-SENSITIVE - LAA Use Only.csv"
    return StreamingResponse(
        chunks,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get(
    "/audit-trail",
    dependencies=[
        Depends(
            audit_and_require_permission(
                possible_permissions=Permission.REPORTS_MI_READ,
                audit_event_factory=ReportAuditEventFactory(
                    report_type=ReportType.AUDIT_TRAIL
                ),
            )
        ),
    ],
)
def get_audit_trail_report(
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
    use_case: GenerateAuditTrailReportUseCase = Depends(
        get_generate_audit_trail_report_use_case
    ),
    request: Request = None,
) -> Response:
    """Generate a CSV of auditable user and system activity between two dates (inclusive)."""

    try:
        csv_content = use_case.execute(from_date, to_date)
    except InvalidDateRangeError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid date range: {exc}",
        )
    except (
        ReportGenerationError,
        ProviderDetailsRetrievalError,
        SQLAlchemyError,
    ) as exc:
        logger.error(
            "Audit trail report generation failed",
            extra=build_log_extra(
                event="audit_trail_report_failed",
                route=_route(request),
                method=_method(request),
                status_code=500,
                error_type=type(exc).__name__,
            ),
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to generate audit trail report",
        )
    filename = f"{datetime.now(UTC).strftime('%Y-%m-%d-%H%M%S')} - Report - IDDS User Audit Trail - OFFICIAL-SENSITIVE - LAA Use Only.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
