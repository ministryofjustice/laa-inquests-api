import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.adapters.application_repository_adapter import ApplicationRepositoryAdapter
from app.adapters.claim_repository_adapter import ClaimRepositoryAdapter
from app.db import get_session
from app.logging_utils import build_log_extra
from app.ports.application_backlog_port import ApplicationBacklogPort
from app.ports.claim_backlog_port import ClaimBacklogPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.routers.applications import get_provider_details_port
from app.routers.dependencies import verify_entra_caseworker_token
from app.use_cases.exceptions import (
    ProviderDetailsRetrievalError,
    ReportGenerationError,
)
from app.use_cases.generate_application_backlog_report import (
    GenerateApplicationBacklogReportUseCase,
)
from app.use_cases.generate_claim_backlog_report import (
    GenerateClaimBacklogReportUseCase,
)

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)

# COPILOT TODO: There is so much logging in the router files. It makes me think we should be aiming to handle these at a higher level or with some kind of abstraction
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


@router.get("/applications/backlog")
def get_application_backlog_report(
    use_case: GenerateApplicationBacklogReportUseCase = Depends(
        get_generate_application_backlog_report_use_case
    ),
    request: Request = None,
    _: None = Depends(verify_entra_caseworker_token),
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


@router.get("/claims/backlog")
def get_claim_backlog_report(
    use_case: GenerateClaimBacklogReportUseCase = Depends(
        get_generate_claim_backlog_report_use_case
    ),
    request: Request = None,
    _: None = Depends(verify_entra_caseworker_token),
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
