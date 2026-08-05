from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.adapters.application_repository_adapter import ApplicationRepositoryAdapter
from app.db import get_session
from app.ports.application_backlog_port import ApplicationBacklogPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.routers.applications import get_provider_details_port
from app.routers.dependencies import verify_entra_caseworker_token
from app.use_cases.generate_application_backlog_report import (
    GenerateApplicationBacklogReportUseCase,
)

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)


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


@router.get("/applications/backlog")
def get_application_backlog_report(
    use_case: GenerateApplicationBacklogReportUseCase = Depends(
        get_generate_application_backlog_report_use_case
    ),
    _: None = Depends(verify_entra_caseworker_token),
) -> StreamingResponse:
    """Generate a CSV report of all open application cases pending assessment or decision."""
    try:
        csv_content = use_case.execute()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate application backlog report",
        )

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=application_backlog_report.csv"
        },
    )
