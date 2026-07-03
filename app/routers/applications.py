from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File
from sqlmodel import Session
from fastapi.responses import StreamingResponse
from typing import Sequence
from mimetypes import guess_type

from app.adapters.sds_adapter import SdsAdapter
from app.adapters.application_repository_adapter import ApplicationRepositoryAdapter
from app.db import get_session
from app.models.application.index import (
    Application,
    ApplicationCreate,
    ApplicationResponse,
    ApplicationSearchResponse,
    MeritsDecisionUpdateGrant,
    MeritsDecisionUpdateRefuse,
    UploadCoronersLetterResponse,
)

from app.adapters.provider_details_adapter import ProviderDetailsAdapter
from app.routers.dependencies import (
    verify_entra_caseworker_token,
    verify_entra_provider_token,
)
from app.config import Config
from app.ports.create_application_port import CreateApplicationPort
from app.ports.get_application_port import GetApplicationPort
from app.ports.update_decision_port import ApplicationDecisionPort
from app.ports.list_applications_port import ListApplicationsPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.ports.search_application_port import SearchApplicationPort
from app.ports.sds_port import SdsPort
from app.ports.upload_coroners_letter_port import UploadCoronersLetterPort
from app.use_cases.create_application import CreateApplicationUseCase
from app.use_cases.get_application import GetApplicationUseCase
from app.use_cases.exceptions import (
    ApplicationNotFoundError,
    CoronersLetterNotFoundError,
    CoronersLetterRetrievalError,
    CoronersLetterUploadError,
    InvalidCoronersLetterDocumentIdError,
    ProceedingsNotFoundError,
)
from app.use_cases.search_application import SearchApplicationUseCase
from app.adapters.gov_notify import GovNotifyAdapter
from app.ports.gov_notify_port import GovNotifyPort
from app.use_cases.list_applications import ListApplicationsUseCase
from app.use_cases.refuse_decision import RefuseDecisionUseCase
from app.use_cases.grant_decision import GrantDecisionUseCase
from app.use_cases.upload_coroners_letter import UploadCoronersLetterUseCase
from app.use_cases.retrieve_coroners_letter import RetrieveCoronersLetterUseCase


router = APIRouter(
    prefix="/applications",
    tags=["Applications"],
    responses={404: {"description": "Not found"}},
)


def get_provider_details_port() -> ProviderDetailsPort:
    return ProviderDetailsAdapter(
        base_url=Config.PROVIDER_API_BASE_URL, api_key=Config.PROVIDER_API_KEY
    )


def get_gov_notify_port() -> GovNotifyPort:
    return GovNotifyAdapter()


def get_sds_port() -> SdsPort:
    return SdsAdapter(
        base_url=Config.SDS_BASE_URL,
        tenant_id=Config.SDS_TENANT_ID,
        client_id=Config.SDS_CLIENT_ID,
        client_secret=Config.SDS_CLIENT_SECRET,
        scope=Config.SDS_SCOPE,
    )


def get_application_db_adapter(
    session: Session = Depends(get_session),
) -> ApplicationRepositoryAdapter:
    return ApplicationRepositoryAdapter(session=session)


def get_get_application_use_case(
    get_application_port: GetApplicationPort = Depends(get_application_db_adapter),
    provider_details_port: ProviderDetailsPort = Depends(get_provider_details_port),
) -> GetApplicationUseCase:
    return GetApplicationUseCase(
        get_application_port=get_application_port,
        provider_details_port=provider_details_port,
    )


def get_create_application_use_case(
    create_application_port: CreateApplicationPort = Depends(
        get_application_db_adapter
    ),
    gov_notify_port: GovNotifyPort = Depends(get_gov_notify_port),
) -> CreateApplicationUseCase:
    return CreateApplicationUseCase(
        create_application_port=create_application_port,
        gov_notify_port=gov_notify_port,
    )


def get_list_applications_use_case(
    list_applications_port: ListApplicationsPort = Depends(get_application_db_adapter),
) -> ListApplicationsUseCase:
    return ListApplicationsUseCase(list_applications_port=list_applications_port)


def get_search_application_use_case(
    search_application_port: SearchApplicationPort = Depends(
        get_application_db_adapter
    ),
    provider_details_port: ProviderDetailsPort = Depends(get_provider_details_port),
) -> SearchApplicationUseCase:
    return SearchApplicationUseCase(
        search_application_port=search_application_port,
        provider_details_port=provider_details_port,
    )


def get_make_merits_decision_use_case(
    update_decision_port: ApplicationDecisionPort = Depends(get_application_db_adapter),
    gov_notify_port: GovNotifyPort = Depends(get_gov_notify_port),
) -> RefuseDecisionUseCase:
    return RefuseDecisionUseCase(
        application_decision_port=update_decision_port,
        gov_notify_port=gov_notify_port,
    )


def get_grant_decision_use_case(
    update_decision_port: ApplicationDecisionPort = Depends(get_application_db_adapter),
) -> GrantDecisionUseCase:
    return GrantDecisionUseCase(
        application_decision_port=update_decision_port,
    )


def get_upload_coroners_letter_use_case(
    sds_port: SdsPort = Depends(get_sds_port),
    upload_coroners_letter_port: UploadCoronersLetterPort = Depends(
        get_application_db_adapter
    ),
) -> UploadCoronersLetterUseCase:
    return UploadCoronersLetterUseCase(
        sds_port=sds_port,
        upload_coroners_letter_port=upload_coroners_letter_port,
    )


@router.get("/search", response_model=list[ApplicationSearchResponse])
async def search_application(
    laa_reference: str,
    use_case: SearchApplicationUseCase = Depends(get_search_application_use_case),
    _: None = Depends(verify_entra_provider_token),
) -> list[ApplicationSearchResponse]:
    """Search for an application by exact LAA reference number."""
    return use_case.execute(laa_reference)


def get_coroners_letter_use_case(
    session: Session = Depends(get_session),
    sds_port: SdsPort = Depends(get_sds_port),
) -> RetrieveCoronersLetterUseCase:
    return RetrieveCoronersLetterUseCase(session=session, sds_port=sds_port)


@router.get(
    "/{laa_reference}/coroners-letter",
    response_class=StreamingResponse,
    responses={200: {"content": {"image/png": {}}}},
)
def retrieve_coroners_letter(
    laa_reference: str,
    use_case: RetrieveCoronersLetterUseCase = Depends(get_coroners_letter_use_case),
    _: None = Depends(verify_entra_caseworker_token),
) -> StreamingResponse:
    """Stream the coroner's letter for a given application."""
    try:
        result = use_case.execute(laa_reference)
    except CoronersLetterNotFoundError:
        raise HTTPException(status_code=404, detail="Coroners letter not found")
    except InvalidCoronersLetterDocumentIdError:
        raise HTTPException(
            status_code=400,
            detail="Invalid coroners letter document id",
        )
    except CoronersLetterRetrievalError:
        raise HTTPException(
            status_code=500, detail="Failed to retrieve coroners letter"
        )

    mime_type = guess_type(result.file_name)
    supported_mime_types = ["image/png", "image/jpeg", "image/bmp", "application/pdf"]
    if mime_type[0] not in supported_mime_types:
        raise HTTPException(
            status_code=415,
            detail="Returned file type is not supported for streaming. Supported file types are: .png, .jpg, .jpeg, .bmp, .pdf",
        )

    return StreamingResponse(
        result.content,
        media_type=mime_type[0],
        headers={"Content-Disposition": f'inline; filename="{result.file_name}"'},
    )


@router.get("/{laa_reference}", response_model=ApplicationResponse)
async def read_application(
    laa_reference: str,
    use_case: GetApplicationUseCase = Depends(get_get_application_use_case),
    _: None = Depends(verify_entra_caseworker_token),
) -> ApplicationResponse:
    """Get information about a given application."""
    try:
        return use_case.execute(laa_reference)
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found")


@router.get("/")
async def read_all_applications(
    use_case: ListApplicationsUseCase = Depends(get_list_applications_use_case),
    _: None = Depends(verify_entra_caseworker_token),
) -> Sequence[Application]:
    """Read all the applications currently in the database."""
    return use_case.execute()


@router.post(
    "/upload-coroners-letter",
    response_model=UploadCoronersLetterResponse,
    status_code=201,
)
async def upload_coroners_letter(
    file: UploadFile = File(...),
    use_case: UploadCoronersLetterUseCase = Depends(
        get_upload_coroners_letter_use_case
    ),
    _: None = Depends(verify_entra_provider_token),
) -> UploadCoronersLetterResponse:
    """Upload a coroner's letter to document storage and return its file ID."""
    contents = await file.read()
    file_name = file.filename
    try:
        coroners_letter_id = use_case.execute(
            contents,
            file_name,
        )
    except CoronersLetterUploadError:
        raise HTTPException(status_code=500, detail="Failed to upload coroners letter")

    return UploadCoronersLetterResponse(
        coroners_letter_id=coroners_letter_id, coroners_letter_file_name=file_name
    )


@router.post("/", response_model=ApplicationResponse, status_code=201)
def create_application(
    request: ApplicationCreate,
    use_case: CreateApplicationUseCase = Depends(get_create_application_use_case),
    _: None = Depends(verify_entra_provider_token),
) -> Application:
    """Creates a new application with proceedings and public bodies."""
    return use_case.execute(request)


@router.patch("/{laa_reference}/refuse-decision", status_code=204)
def refuse_decision(
    laa_reference: str,
    request: MeritsDecisionUpdateRefuse,
    use_case: RefuseDecisionUseCase = Depends(get_make_merits_decision_use_case),
    _: None = Depends(verify_entra_caseworker_token),
) -> Response:
    """Set the merits decision on the single proceeding for a given application."""
    try:
        use_case.execute(laa_reference, request)
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found")
    except ProceedingsNotFoundError:
        raise HTTPException(
            status_code=404, detail="No proceedings found for application"
        )

    return Response(status_code=204)


@router.patch("/{laa_reference}/grant-decision", status_code=204)
def grant_decision(
    laa_reference: str,
    request: MeritsDecisionUpdateGrant,
    use_case: GrantDecisionUseCase = Depends(get_grant_decision_use_case),
    _: None = Depends(verify_entra_caseworker_token),
) -> Response:
    """Grant the merits decision on the single proceeding for a given application."""
    try:
        use_case.execute(laa_reference, request)
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found")
    except ProceedingsNotFoundError:
        raise HTTPException(
            status_code=404, detail="No proceedings found for application"
        )

    return Response(status_code=204)
