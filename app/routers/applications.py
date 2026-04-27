from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from typing import Sequence
from uuid import UUID

from app.auth.security import get_current_active_user
from app.db import get_session
from app.models.application.index import Application, ApplicationRequest
from app.models.user import User


router = APIRouter(
    prefix="/applications",
    tags=["Applications"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{application_id}")
async def read_application(application_id: str, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user),) -> Application:
    """Get information about a given application."""
    print("helelo")
    application = session.get(Application, UUID(application_id))
    return application


@router.get("/")
async def read_all_applications(session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user),) -> Sequence[Application]:
    """Read all the applications currently in the database."""
    applications = session.exec(select(Application)).all()
    return applications


@router.post("/", response_model=Application)
def create_application(request: ApplicationRequest, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user),) -> Application:
    """Creates a new application."""
    application = Application(**request.model_dump())
    session.add(application)
    session.commit()
    session.refresh(application)
    return application