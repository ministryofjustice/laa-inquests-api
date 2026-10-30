from collections.abc import Callable
from contextlib import AbstractContextManager

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.adapters.database_readiness_adapter import DatabaseReadinessAdapter
from app.db import CustomSessionLocal
from app.ports.check_readiness_port import ReadinessUnavailableError
from app.use_cases.check_readiness import CheckReadinessUseCase

router = APIRouter(
    tags=["Monitoring"],
)


def get_readiness_session_factory() -> Callable[[], AbstractContextManager[Session]]:
    return CustomSessionLocal


def get_readiness_use_case(
    session_factory: Callable[[], AbstractContextManager[Session]] = Depends(
        get_readiness_session_factory
    ),
) -> CheckReadinessUseCase:
    return CheckReadinessUseCase(DatabaseReadinessAdapter(session_factory))


@router.get("/health")
def health_check() -> str:
    return "Healthy"


@router.get("/status")
def status_check(
    use_case: CheckReadinessUseCase = Depends(get_readiness_use_case),
) -> str:
    try:
        use_case.execute()
    except ReadinessUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Service unavailable") from exc
    return "OK"
