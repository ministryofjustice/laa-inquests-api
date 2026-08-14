import logging
from collections.abc import Sequence
from mimetypes import guess_type
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from sqlmodel import Session

from app.adapters.application_repository_adapter import ApplicationRepositoryAdapter
from app.adapters.gov_notify import GovNotifyAdapter
from app.adapters.history_event_repository_adapter import HistoryEventRepositoryAdapter
from app.adapters.pdf_generator_adapter import PdfGeneratorAdapter
from app.adapters.provider_details_adapter import ProviderDetailsAdapter
from app.config import Config
from app.db import get_session
from app.logging_utils import build_log_extra
from app.models.application.certificate import ApplicationCertificateResponse
from app.models.application.enums import MeritsDecision
from app.models.application.index import (
    Application,
    ApplicationCreate,
    ApplicationResponse,
    ApplicationSearchResponse,
    GrantApplicationUpdate,
    PublicBody,
    PublicBodyResponse,
    RefuseApplicationUpdate,
    UploadCoronersLetterResponse,
)
from app.models.claim.index import (
    ClaimByIdResponse,
    ClaimCreate,
    ClaimResponse,
    ClaimSummaryResponse,
)
from app.models.history.index import HistoryEventResponse
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.create_claim_decision_port import CreateClaimDecisionPort
from app.ports.claim.create_claim_port import CreateClaimPort
from app.ports.claim.create_decision_reason_port import CreateDecisionReasonPort
from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.ports.claim.get_claim_decision_port import GetClaimDecisionPort
from app.ports.claim.get_claims_for_application_port import GetClaimsForApplicationPort
from app.ports.claim.update_claim_status_port import (
    UpdateClaimStatusPort,
)
from app.ports.create_application_port import CreateApplicationPort
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.ports.entra_auth_port import AuthenticatedUser
from app.ports.get_application_history_port import GetApplicationHistoryPort
from app.ports.get_application_port import GetApplicationPort
from app.ports.gov_notify_port import GovNotifyPort
from app.ports.list_applications_port import ListApplicationsPort
from app.ports.list_public_bodies_port import ListPublicBodiesPort
from app.ports.pdf_generation_port import PdfGenerationPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.ports.sds_port import SdsPort
from app.ports.search_application_port import SearchApplicationPort
from app.ports.update_decision_port import ApplicationDecisionPort
from app.ports.upload_coroners_letter_port import UploadCoronersLetterPort
from app.routers.dependencies import (
    get_claim_db_adapter,
    get_current_provider_firm_code,
    get_sds_port,
    verify_entra_caseworker_token,
    verify_entra_provider_token,
)
from app.use_cases.create_application import CreateApplicationUseCase
from app.use_cases.create_certificate_context import CreateCertificateContextUseCase
from app.use_cases.create_claim import CreateClaimCommand, CreateClaimUseCase
from app.use_cases.exceptions import (
    ApplicationNotFoundError,
    ApplicationNotGrantedError,
    ClaimNotFoundError,
    CoronersLetterNotFoundError,
    CoronersLetterRetrievalError,
    CoronersLetterUploadError,
    CoronersLetterVirusDetectedError,
    InvalidClaimError,
    InvalidCoronersLetterDocumentIdError,
    ProviderDetailsRetrievalError,
)
from app.use_cases.get_application import GetApplicationUseCase
from app.use_cases.get_application_history import GetApplicationHistoryUseCase
from app.use_cases.get_claim import GetClaimUseCase
from app.use_cases.grant_decision import GrantDecisionUseCase
from app.use_cases.list_application_claims import ListApplicationClaimsUseCase
from app.use_cases.list_applications import ListApplicationsUseCase
from app.use_cases.list_public_bodies import ListPublicBodiesUseCase
from app.use_cases.refuse_decision import RefuseDecisionUseCase
from app.use_cases.retrieve_certificate import RetrieveCertificateUseCase
from app.use_cases.retrieve_coroners_letter import RetrieveCoronersLetterUseCase
from app.use_cases.search_application import SearchApplicationUseCase
from app.use_cases.send_grant_email import SendGrantEmailUseCase
from app.use_cases.send_grant_letter import SendGrantLetterUseCase
from app.use_cases.upload_coroners_letter import UploadCoronersLetterUseCase

router = APIRouter(
    prefix="/applications",
    tags=["Applications"],
    responses={404: {"description": "Not found"}},
)

# COPILOT TODO: There is so much logging in the router files. It makes me think we should be aiming to handle these at a higher level or with some kind of abstraction
logger = logging.getLogger(__name__)


def _route(request: Request | None) -> str | None:
    return request.url.path if request is not None else None


def _method(request: Request | None) -> str | None:
    return request.method if request is not None else None


def get_provider_details_port() -> ProviderDetailsPort:
    return ProviderDetailsAdapter(
        base_url=Config.PROVIDER_API_BASE_URL, api_key=Config.PROVIDER_API_KEY
    )


def get_gov_notify_port() -> GovNotifyPort:
    return GovNotifyAdapter()


def get_pdf_generation_port() -> PdfGenerationPort:
    return PdfGeneratorAdapter()


def get_application_db_adapter(
    session: Session = Depends(get_session),
) -> ApplicationRepositoryAdapter:
    return ApplicationRepositoryAdapter(session=session)


def get_history_event_adapter(
    session: Session = Depends(get_session),
) -> HistoryEventRepositoryAdapter:
    return HistoryEventRepositoryAdapter(session=session)


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
    create_history_event_port: CreateHistoryEventPort = Depends(
        get_history_event_adapter
    ),
    gov_notify_port: GovNotifyPort = Depends(get_gov_notify_port),
) -> CreateApplicationUseCase:
    return CreateApplicationUseCase(
        create_application_port=create_application_port,
        create_history_event_port=create_history_event_port,
        gov_notify_port=gov_notify_port,
    )


def get_application_history_use_case(
    get_application_history_port: GetApplicationHistoryPort = Depends(
        get_history_event_adapter
    ),
    get_application_port: GetApplicationPort = Depends(get_application_db_adapter),
) -> GetApplicationHistoryUseCase:
    return GetApplicationHistoryUseCase(
        get_application_history_port=get_application_history_port,
        get_application_port=get_application_port,
    )


def get_list_applications_use_case(
    list_applications_port: ListApplicationsPort = Depends(get_application_db_adapter),
) -> ListApplicationsUseCase:
    return ListApplicationsUseCase(list_applications_port=list_applications_port)


def get_list_public_bodies_use_case(
    list_public_bodies_port: ListPublicBodiesPort = Depends(get_application_db_adapter),
) -> ListPublicBodiesUseCase:
    return ListPublicBodiesUseCase(list_public_bodies_port=list_public_bodies_port)


def get_list_application_claims_use_case(
    get_claims_for_application_port: GetClaimsForApplicationPort = Depends(
        get_claim_db_adapter
    ),
    get_claim_decision_port: GetClaimDecisionPort = Depends(get_claim_db_adapter),
    application_lookup_port: ApplicationLookupPort = Depends(
        get_application_db_adapter
    ),
) -> ListApplicationClaimsUseCase:
    return ListApplicationClaimsUseCase(
        get_claims_for_application_port=get_claims_for_application_port,
        get_claim_decision_port=get_claim_decision_port,
        application_lookup_port=application_lookup_port,
    )


def get_get_claim_use_case(
    get_claim_by_id_port: GetClaimByIdPort = Depends(get_claim_db_adapter),
    get_claim_decision_port: GetClaimDecisionPort = Depends(get_claim_db_adapter),
    application_lookup_port: ApplicationLookupPort = Depends(
        get_application_db_adapter
    ),
) -> GetClaimUseCase:
    return GetClaimUseCase(
        get_claim_by_id_port=get_claim_by_id_port,
        get_claim_decision_port=get_claim_decision_port,
        application_lookup_port=application_lookup_port,
    )


def get_create_claim_use_case(
    create_claim_port: CreateClaimPort = Depends(get_claim_db_adapter),
    create_claim_decision_port: CreateClaimDecisionPort = Depends(get_claim_db_adapter),
    create_decision_reason_port: CreateDecisionReasonPort = Depends(
        get_claim_db_adapter
    ),
    update_claim_status_port: UpdateClaimStatusPort = Depends(get_claim_db_adapter),
    application_lookup_port: ApplicationLookupPort = Depends(
        get_application_db_adapter
    ),
    get_claims_for_application_port: GetClaimsForApplicationPort = Depends(
        get_claim_db_adapter
    ),
    get_claim_decision_port: GetClaimDecisionPort = Depends(get_claim_db_adapter),
    gov_notify_port: GovNotifyPort = Depends(get_gov_notify_port),
) -> CreateClaimUseCase:
    return CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=application_lookup_port,
        get_claims_for_application_port=get_claims_for_application_port,
        gov_notify_port=gov_notify_port,
        create_claim_decision_port=create_claim_decision_port,
        create_decision_reason_port=create_decision_reason_port,
        update_claim_status_port=update_claim_status_port,
        get_claim_decision_port=get_claim_decision_port,
    )


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
    create_history_event_port: CreateHistoryEventPort = Depends(
        get_history_event_adapter
    ),
) -> RefuseDecisionUseCase:
    return RefuseDecisionUseCase(
        application_decision_port=update_decision_port,
        gov_notify_port=gov_notify_port,
        create_history_event_port=create_history_event_port,
    )


def get_create_certificate_context_use_case(
    provider_details_port: ProviderDetailsPort = Depends(get_provider_details_port),
) -> CreateCertificateContextUseCase:
    return CreateCertificateContextUseCase(
        provider_details_port=provider_details_port,
    )


def get_retrieve_certificate_use_case(
    get_application_port: GetApplicationPort = Depends(get_application_db_adapter),
    create_certificate_context_use_case: CreateCertificateContextUseCase = Depends(
        get_create_certificate_context_use_case
    ),
) -> RetrieveCertificateUseCase:
    return RetrieveCertificateUseCase(
        get_application_port=get_application_port,
        create_certificate_context_use_case=create_certificate_context_use_case,
    )


def get_grant_decision_use_case(
    update_decision_port: ApplicationDecisionPort = Depends(get_application_db_adapter),
    gov_notify_port: GovNotifyPort = Depends(get_gov_notify_port),
    pdf_generation_port: PdfGenerationPort = Depends(get_pdf_generation_port),
    create_history_event_port: CreateHistoryEventPort = Depends(
        get_history_event_adapter
    ),
    create_certificate_context_use_case=Depends(
        get_create_certificate_context_use_case
    ),
) -> GrantDecisionUseCase:
    send_grant_email_use_case = SendGrantEmailUseCase(
        pdf_generation_port=pdf_generation_port,
        gov_notify_port=gov_notify_port,
    )
    send_grant_letter_use_case = SendGrantLetterUseCase(
        pdf_generation_port=pdf_generation_port,
        gov_notify_port=gov_notify_port,
    )
    return GrantDecisionUseCase(
        application_decision_port=update_decision_port,
        create_certificate_context_use_case=create_certificate_context_use_case,
        send_grant_email_use_case=send_grant_email_use_case,
        send_grant_letter_use_case=send_grant_letter_use_case,
        create_history_event_port=create_history_event_port,
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
    firm_code: Annotated[str, Depends(get_current_provider_firm_code)],
    merits_decision: MeritsDecision | None = None,
    request: Request = None,
    use_case: SearchApplicationUseCase = Depends(get_search_application_use_case),
) -> list[ApplicationSearchResponse]:
    """Search for an application by exact LAA reference number."""
    try:
        results = use_case.execute(laa_reference, firm_code, merits_decision)
        logger.info(
            "Application search completed",
            extra=build_log_extra(
                event="application_search_completed",
                route=_route(request),
                method=_method(request),
                status_code=200,
                laa_reference=laa_reference,
                firm_code=firm_code,
                merits_decision=merits_decision.value if merits_decision else None,
                result_count=len(results),
            ),
        )
        return results
    except ProviderDetailsRetrievalError:
        logger.warning(
            "Application search failed",
            extra=build_log_extra(
                event="application_search_failed",
                route=_route(request),
                method=_method(request),
                status_code=500,
                laa_reference=laa_reference,
                firm_code=firm_code,
            ),
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve firm name from provider details service",
        )


@router.get("/public-bodies", response_model=list[PublicBodyResponse])
def list_public_bodies(
    use_case: ListPublicBodiesUseCase = Depends(get_list_public_bodies_use_case),
    request: Request = None,
    _: None = Depends(verify_entra_provider_token),
) -> list[PublicBody]:
    public_bodies = use_case.execute()
    logger.info(
        "Listed public bodies",
        extra=build_log_extra(
            event="list_public_bodies_completed",
            route=_route(request),
            method=_method(request),
            status_code=200,
            result_count=len(public_bodies),
        ),
    )
    return public_bodies


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
    request: Request = None,
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

    logger.info(
        "Coroners letter retrieved",
        extra=build_log_extra(
            event="coroners_letter_retrieved",
            route=_route(request),
            method=_method(request),
            status_code=200,
            laa_reference=laa_reference,
            file_name=result.file_name,
        ),
    )

    return StreamingResponse(
        result.content,
        media_type=mime_type[0],
        headers={"Content-Disposition": f'inline; filename="{result.file_name}"'},
    )


@router.get(
    "/{laa_reference}/claims",
    response_model=list[ClaimSummaryResponse],
)
def list_application_claims(
    laa_reference: str,
    assessed: bool,
    use_case: ListApplicationClaimsUseCase = Depends(
        get_list_application_claims_use_case
    ),
    request: Request = None,
    _: None = Depends(verify_entra_caseworker_token),
) -> list[ClaimSummaryResponse]:
    """List claims for an application, filtered by assessed status."""
    try:
        claims = use_case.execute(laa_reference, assessed)
        logger.info(
            "Application claims listed",
            extra=build_log_extra(
                event="application_claims_listed",
                route=_route(request),
                method=_method(request),
                status_code=200,
                laa_reference=laa_reference,
                assessed=assessed,
                result_count=len(claims),
            ),
        )
        return claims
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found")


@router.get(
    "/{laa_reference}/claims/{claim_id}",
    response_model=ClaimByIdResponse,
)
def read_claim(
    laa_reference: str,
    claim_id: int,
    use_case: GetClaimUseCase = Depends(get_get_claim_use_case),
    request: Request = None,
    _: None = Depends(verify_entra_caseworker_token),
) -> ClaimByIdResponse:
    """Get a single claim by ID for a given application."""
    try:
        claim = use_case.execute(laa_reference, claim_id)
        logger.info(
            "Claim retrieved",
            extra=build_log_extra(
                event="claim_retrieved",
                route=_route(request),
                method=_method(request),
                status_code=200,
                laa_reference=laa_reference,
                claim_id=claim_id,
            ),
        )
        return claim
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found")
    except ClaimNotFoundError:
        raise HTTPException(status_code=404, detail="Claim not found")


@router.get("/{laa_reference}", response_model=ApplicationResponse)
async def read_application(
    laa_reference: str,
    use_case: GetApplicationUseCase = Depends(get_get_application_use_case),
    request: Request = None,
    _: None = Depends(verify_entra_caseworker_token),
) -> ApplicationResponse:
    """Get information about a given application."""
    try:
        application = use_case.execute(laa_reference)
        logger.info(
            "Application retrieved",
            extra=build_log_extra(
                event="application_retrieved",
                route=_route(request),
                method=_method(request),
                status_code=200,
                laa_reference=laa_reference,
            ),
        )
        return application
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found")


@router.get(
    "/{laa_reference}/certificate",
    response_model=ApplicationCertificateResponse,
)
def read_certificate(
    laa_reference: str,
    use_case: RetrieveCertificateUseCase = Depends(get_retrieve_certificate_use_case),
    request: Request = None,
    _: None = Depends(verify_entra_caseworker_token),
) -> ApplicationCertificateResponse:
    """Get the populated certificate context for a given application."""
    try:
        certificate = use_case.execute(laa_reference)
        logger.info(
            "Certificate context retrieved",
            extra=build_log_extra(
                event="certificate_context_retrieved",
                route=_route(request),
                method=_method(request),
                status_code=200,
                laa_reference=laa_reference,
            ),
        )
        return ApplicationCertificateResponse.model_validate(certificate)
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found")
    except ApplicationNotGrantedError:
        raise HTTPException(
            status_code=422,
            detail="Application is not granted",
        )
    except ProviderDetailsRetrievalError:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve firm name from provider details service",
        )


@router.get(
    "/{laa_reference}/history",
    response_model=list[HistoryEventResponse],
)
def get_application_history(
    laa_reference: str,
    use_case: GetApplicationHistoryUseCase = Depends(get_application_history_use_case),
    request: Request = None,
    _: None = Depends(verify_entra_caseworker_token),
) -> list[HistoryEventResponse]:
    """Get the history of a given application."""
    try:
        history = use_case.execute(laa_reference)
        logger.info(
            "Application history retrieved",
            extra=build_log_extra(
                event="application_history_retrieved",
                route=_route(request),
                method=_method(request),
                status_code=200,
                laa_reference=laa_reference,
                result_count=len(history),
            ),
        )
        return history
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found")


@router.get("/")
async def read_all_applications(
    use_case: ListApplicationsUseCase = Depends(get_list_applications_use_case),
    request: Request = None,
    _: None = Depends(verify_entra_caseworker_token),
) -> Sequence[Application]:
    """Read all the applications currently in the database."""
    applications = use_case.execute()
    logger.info(
        "All applications listed",
        extra=build_log_extra(
            event="all_applications_listed",
            route=_route(request),
            method=_method(request),
            status_code=200,
            result_count=len(applications),
        ),
    )
    return applications


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
    request: Request = None,
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
    except CoronersLetterVirusDetectedError:
        logger.warning(
            "Coroners letter upload failed virus check",
            extra=build_log_extra(
                event="coroners_letter_uploaded_failed",
                route=_route(request),
                method=_method(request),
                status_code=422,
                file_name=file_name,
            ),
        )
        raise HTTPException(status_code=422, detail="Uploaded file failed virus check")
    except CoronersLetterUploadError:
        logger.warning(
            "Coroners letter upload failed",
            extra=build_log_extra(
                event="coroners_letter_uploaded_failed",
                route=_route(request),
                method=_method(request),
                status_code=500,
                file_name=file_name,
            ),
        )
        raise HTTPException(status_code=500, detail="Failed to upload coroners letter")

    logger.info(
        "Coroners letter uploaded",
        extra=build_log_extra(
            event="coroners_letter_uploaded_success",
            route=_route(request),
            method=_method(request),
            status_code=201,
            coroners_letter_id=str(coroners_letter_id),
            file_name=file_name,
        ),
    )

    return UploadCoronersLetterResponse(
        coroners_letter_id=coroners_letter_id, coroners_letter_file_name=file_name
    )


@router.post("/", response_model=ApplicationResponse, status_code=201)
def create_application(
    request: ApplicationCreate,
    firm_code: Annotated[str, Depends(get_current_provider_firm_code)],
    use_case: CreateApplicationUseCase = Depends(get_create_application_use_case),
    http_request: Request = None,
) -> Application:
    """Creates a new application with proceedings and public bodies."""
    application = use_case.execute(request, firm_code)
    logger.info(
        "Application created",
        extra=build_log_extra(
            event="application_created_success",
            route=_route(http_request),
            method=_method(http_request),
            status_code=201,
            laa_reference=application.laa_reference,
            firm_code=firm_code,
        ),
    )
    return application


@router.post(
    "/{laa_reference}/claim",
    response_model=ClaimResponse,
    status_code=201,
)
def create_claim(
    laa_reference: str,
    request: ClaimCreate,
    firm_code: Annotated[str, Depends(get_current_provider_firm_code)],
    use_case: CreateClaimUseCase = Depends(get_create_claim_use_case),
    http_request: Request = None,
) -> ClaimResponse:
    """Creates a new claim against an application."""
    try:
        command = CreateClaimCommand(
            laa_reference=laa_reference,
            firm_code=firm_code,
            claim_type=request.claim_type,
            poa_type=request.poa_type_id,
            net=request.total_profit_cost_net,
            gross=request.total_profit_cost_gross,
            vat_zero_total=request.total_profit_cost_vat_zero,
            claimant_id=request.claimant_id,
            claim_evidence_ids=request.claim_evidence_ids,
        )
        result = use_case.execute(command)
        response = ClaimResponse(claim_id=result.claim.claim_id)
        if result.rejection_reasons is not None:
            response = response.model_copy(
                update={"rejection_reasons": result.rejection_reasons}
            )
            payload = response.model_dump(by_alias=True)
        else:
            payload = response.model_dump(
                by_alias=True,
                exclude={"rejection_reasons"},
            )
        logger.info(
            "Claim created",
            extra=build_log_extra(
                event="claim_created_success",
                route=_route(http_request),
                method=_method(http_request),
                status_code=201,
                laa_reference=laa_reference,
                claim_id=result.claim.claim_id,
                has_rejection_reasons=result.rejection_reasons is not None,
            ),
        )
        return JSONResponse(content=jsonable_encoder(payload), status_code=201)
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found")
    except InvalidClaimError as e:
        raise HTTPException(
            status_code=422, detail={"errorCode": e.code, "message": e.message}
        )


@router.patch("/{laa_reference}/refuse-decision", status_code=204)
def refuse_decision(
    laa_reference: str,
    request: RefuseApplicationUpdate,
    use_case: RefuseDecisionUseCase = Depends(get_make_merits_decision_use_case),
    user: AuthenticatedUser = Depends(verify_entra_caseworker_token),
    http_request: Request = None,
) -> Response:
    """Set the merits decision on the single proceeding for a given application."""
    try:
        use_case.execute(laa_reference, request, user.name)
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found")

    logger.info(
        "Application refusal decision recorded",
        extra=build_log_extra(
            event="application_refused_decision_recorded",
            route=_route(http_request),
            method=_method(http_request),
            status_code=204,
            laa_reference=laa_reference,
        ),
    )

    return Response(status_code=204)


@router.patch("/{laa_reference}/grant-decision", status_code=204)
def grant_decision(
    laa_reference: str,
    request: GrantApplicationUpdate,
    use_case: GrantDecisionUseCase = Depends(get_grant_decision_use_case),
    user: AuthenticatedUser = Depends(verify_entra_caseworker_token),
    http_request: Request = None,
) -> Response:
    """Grant the merits decision on the single proceeding for a given application."""
    try:
        use_case.execute(laa_reference, request, user.name)

    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found")

    logger.info(
        "Application grant decision recorded",
        extra=build_log_extra(
            event="application_granted_decision_recorded",
            route=_route(http_request),
            method=_method(http_request),
            status_code=204,
            laa_reference=laa_reference,
        ),
    )

    return Response(status_code=204)
