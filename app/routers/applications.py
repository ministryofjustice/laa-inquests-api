from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import Sequence
# from app.auth.security import get_current_active_user
from app.db import get_session
from app.models.application.index import (
    Application,
    ApplicationCreate,
    ApplicationProceeding,
    ApplicationResponse,
    ProceedingId,
)
# from app.models.user import User


router = APIRouter(
    prefix="/applications",
    tags=["Applications"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{laa_reference}", response_model=ApplicationResponse)
async def read_application(
    laa_reference: str,
    session: Session = Depends(get_session),
    # current_user: User = Depends(get_current_active_user),
) -> Application:
    """Get information about a given application."""
    application = session.get(Application, int(laa_reference))
    return application


@router.get("/")
async def read_all_applications(
    session: Session = Depends(get_session),
    # current_user: User = Depends(get_current_active_user),
) -> Sequence[Application]:
    """Read all the applications currently in the database."""
    applications = session.exec(select(Application)).all()
    return applications


@router.post("/", response_model=ApplicationResponse)
def create_application(
    request: ApplicationCreate,
    session: Session = Depends(get_session),
    # current_user: User = Depends(get_current_active_user),
) -> Application:
    """Creates a new application with proceedings."""
    proceedings_to_add = []
    for proceeding in request.proceedings:
        code_str = proceeding.proceeding_id
        proceeding_to_add = ApplicationProceeding(proceeding_id=ProceedingId(code_str))
        proceedings_to_add.append(proceeding_to_add)

    new_application = Application(proceedings=proceedings_to_add)
    session.add(new_application)
    session.commit()
    session.refresh(new_application)

    return new_application
