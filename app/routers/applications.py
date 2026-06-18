from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlmodel import Session, select
from typing import Sequence

# from app.auth.security import get_current_active_user
from app.db import get_session
from app.models.application.index import (
    Application,
    ApplicationCreate,
    ApplicationResponse,
    CoronersLetterRequest,
    MeritsDecisionUpdate,
    UploadCoronersLetterResponse,
)
from app.adapters.provider_details_adapter import ProviderDetailsAdapter
from app.adapters.sds_adapter import SdsAdapter
from app.config import Config
from app.ports.provider_details_port import ProviderDetailsPort
from app.ports.sds_port import SdsPort
from app.use_cases.create_application import CreateApplicationUseCase
from app.use_cases.exceptions import ApplicationNotFoundError, CoronersLetterSaveError
from app.use_cases.read_application import ReadApplicationUseCase
from app.use_cases.save_coroners_letter import SaveCoronersLetterUseCase


router = APIRouter(
    prefix="/applications",
    tags=["Applications"],
    responses={404: {"description": "Not found"}},
)


def get_provider_details_port() -> ProviderDetailsPort:
    return ProviderDetailsAdapter(
        base_url=Config.PROVIDER_API_BASE_URL, api_key=Config.PROVIDER_API_KEY
    )


def get_sds_port() -> SdsPort:
    return SdsAdapter(
        base_url=Config.SDS_BASE_URL,
        tenant_id=Config.SDS_TENANT_ID,
        client_id=Config.SDS_CLIENT_ID,
        client_secret=Config.SDS_CLIENT_SECRET,
        scope=Config.SDS_SCOPE,
    )


def get_read_application_use_case(
    session: Session = Depends(get_session),
    provider_details_port: ProviderDetailsPort = Depends(get_provider_details_port),
) -> ReadApplicationUseCase:
    return ReadApplicationUseCase(
        session=session, provider_details_port=provider_details_port
    )


def get_save_coroners_letter_use_case(
    sds_port: SdsPort = Depends(get_sds_port),
) -> SaveCoronersLetterUseCase:
    return SaveCoronersLetterUseCase(sds_port=sds_port)


def get_create_application_use_case(
    session: Session = Depends(get_session),
) -> CreateApplicationUseCase:
    return CreateApplicationUseCase(session=session)


@router.post(
    "/upload-coroners-letter",
    response_model=UploadCoronersLetterResponse,
    status_code=201,
)
async def upload_coroners_letter(
    file: UploadFile = File(...),
    use_case: SaveCoronersLetterUseCase = Depends(get_save_coroners_letter_use_case),
    # current_user: User = Depends(get_current_active_user),
) -> UploadCoronersLetterResponse:
    """Upload a coroner's letter to document storage and return its file ID."""
    contents = await file.read()
    try:
        response = use_case.execute(
            CoronersLetterRequest(
                coroners_letter=contents,
                file_name=file.filename,
            )
        )
    except CoronersLetterSaveError:
        raise HTTPException(status_code=500, detail="Failed to save coroners letter")
    return UploadCoronersLetterResponse(file_id=response.id)


@router.get("/{laa_reference}", response_model=ApplicationResponse)
async def read_application(
    laa_reference: str,
    use_case: ReadApplicationUseCase = Depends(get_read_application_use_case),
    # current_user: User = Depends(get_current_active_user),
) -> ApplicationResponse:
    """Get information about a given application."""
    try:
        return use_case.execute(laa_reference)
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found")


@router.get("/")
async def read_all_applications(
    session: Session = Depends(get_session),
    # current_user: User = Depends(get_current_active_user),
) -> Sequence[Application]:
    """Read all the applications currently in the database."""
    applications = session.exec(select(Application)).all()
    return applications


@router.post("/", response_model=ApplicationResponse, status_code=201)
def create_application(
    request: ApplicationCreate,
    create_use_case: CreateApplicationUseCase = Depends(
        get_create_application_use_case
    ),
    # current_user: User = Depends(get_current_active_user),
) -> Application:
    """Creates a new application with proceedings, public bodies."""
    return create_use_case.execute(request)


@router.patch("/{laa_reference}/merits-decision", status_code=204)
def patch_merits_decision(
    laa_reference: str,
    request: MeritsDecisionUpdate,
    session: Session = Depends(get_session),
    # current_user: User = Depends(get_current_active_user),
) -> Response:
    """Set the merits decision on the single proceeding for a given application."""
    application = session.get(Application, int(laa_reference))
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    if not application.proceedings:
        raise HTTPException(
            status_code=404, detail="No proceedings found for application"
        )

    proceeding = application.proceedings[0]
    proceeding.merits_decision = request.merits_decision

    application.overall_decision = request.merits_decision

    session.add(application)
    session.add(proceeding)
    session.commit()
    return Response(status_code=204)
