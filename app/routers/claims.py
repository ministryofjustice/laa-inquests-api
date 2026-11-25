import logging
import uuid
from mimetypes import add_type, guess_type
from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import StreamingResponse

from app.auth.rbac import Permission, require_permission_from
from app.domain.caller import Caller
from app.logging_utils import build_log_extra
from app.models.claim.index import ClaimApplicationResponse, UploadClaimEvidenceResponse
from app.ports.claim.delete_claim_evidence_port import DeleteClaimEvidencePort
from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.ports.claim.get_claim_evidence_port import GetClaimEvidencePort
from app.ports.claim.upload_claim_evidence_port import UploadClaimEvidencePort
from app.ports.sds_port import SdsPort
from app.routers.content_disposition import content_disposition
from app.routers.dependencies import (
    get_caller,
    get_claim_db_adapter,
    get_current_provider_office_codes,
    get_sds_port,
)
from app.use_cases.delete_claim_evidence import DeleteClaimEvidenceUseCase
from app.use_cases.exceptions import (
    ClaimEvidenceDeleteError,
    ClaimEvidenceNotFoundError,
    ClaimEvidenceRejectedError,
    ClaimEvidenceRetrievalError,
    ClaimEvidenceUploadError,
    ClaimEvidenceVirusDetectedError,
    ClaimNotFoundError,
    InvalidFileNameError,
    ProviderOfficeMismatchError,
)
from app.use_cases.retrieve_application_for_claim import (
    RetrieveApplicationForClaimUseCase,
)
from app.use_cases.retrieve_claim_evidence import RetrieveClaimEvidenceUseCase
from app.use_cases.upload_claim_evidence import UploadClaimEvidenceUseCase

# Ensure Excel types resolve regardless of the OS mime registry (e.g. slim Docker images).
add_type("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx")
add_type("application/vnd.ms-excel", ".xls")

router = APIRouter(
    prefix="/claims",
    tags=["Claims"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)


def _route(request: Request | None) -> str | None:
    return request.url.path if request is not None else None


def _method(request: Request | None) -> str | None:
    return request.method if request is not None else None


def get_claim_evidence_use_case(
    get_claim_evidence_port: GetClaimEvidencePort = Depends(get_claim_db_adapter),
    sds_port: SdsPort = Depends(get_sds_port),
) -> RetrieveClaimEvidenceUseCase:
    return RetrieveClaimEvidenceUseCase(
        get_claim_evidence_port=get_claim_evidence_port,
        sds_port=sds_port,
    )


def get_upload_claim_evidence_use_case(
    sds_port: SdsPort = Depends(get_sds_port),
    upload_claim_evidence_port: UploadClaimEvidencePort = Depends(get_claim_db_adapter),
) -> UploadClaimEvidenceUseCase:
    return UploadClaimEvidenceUseCase(
        sds_port=sds_port,
        upload_claim_evidence_port=upload_claim_evidence_port,
    )


def get_delete_claim_evidence_use_case(
    get_claim_evidence_port: GetClaimEvidencePort = Depends(get_claim_db_adapter),
    delete_claim_evidence_port: DeleteClaimEvidencePort = Depends(get_claim_db_adapter),
    sds_port: SdsPort = Depends(get_sds_port),
) -> DeleteClaimEvidenceUseCase:
    return DeleteClaimEvidenceUseCase(
        get_claim_evidence_port=get_claim_evidence_port,
        delete_claim_evidence_port=delete_claim_evidence_port,
        sds_port=sds_port,
    )


def get_retrieve_application_for_claim_use_case(
    get_claim_by_id_port: GetClaimByIdPort = Depends(get_claim_db_adapter),
) -> RetrieveApplicationForClaimUseCase:
    return RetrieveApplicationForClaimUseCase(
        get_claim_by_id_port=get_claim_by_id_port,
    )


@router.post(
    "/evidence",
    response_model=UploadClaimEvidenceResponse,
    status_code=201,
    dependencies=[Depends(require_permission_from(Permission.CLAIM_CREATE))],
)
async def upload_claim_evidence(
    user_office_codes: Annotated[
        frozenset[str], Depends(get_current_provider_office_codes)
    ],
    office_id: Annotated[
        str,
        Form(
            min_length=1,
            description="Office uploading the evidence; must be one of the user's office codes.",
        ),
    ],
    file: UploadFile = File(...),
    use_case: UploadClaimEvidenceUseCase = Depends(get_upload_claim_evidence_use_case),
    request: Request = None,
) -> UploadClaimEvidenceResponse:
    """Upload claim evidence to document storage and return its file ID.

    Returns 422 if the file name is longer than 255 characters or uses anything other
    than letters a-z/A-Z, numbers, spaces and the characters `.!()_-`.
    """
    contents = await file.read()
    file_name = file.filename
    try:
        claim_evidence_id = use_case.execute(
            contents,
            file_name,
            office_id,
            user_office_codes,
        )
    except ProviderOfficeMismatchError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except InvalidFileNameError:
        raise HTTPException(status_code=422, detail="Invalid file name")
    except ClaimEvidenceRejectedError as e:
        logger.warning(
            "Claim evidence upload rejected",
            extra=build_log_extra(
                event="claim_evidence_uploaded_failed",
                route=_route(request),
                method=_method(request),
                status_code=422,
                reason=e.code,
            ),
        )
        raise HTTPException(
            status_code=422, detail={"code": e.code, "message": e.safe_message}
        ) from None
    except ClaimEvidenceVirusDetectedError:
        logger.warning(
            "Claim evidence upload failed virus check",
            extra=build_log_extra(
                event="claim_evidence_uploaded_failed",
                route=_route(request),
                method=_method(request),
                status_code=422,
                file_name=file_name,
            ),
        )
        raise HTTPException(status_code=422, detail="Uploaded file failed virus check")
    except ClaimEvidenceUploadError:
        logger.warning(
            "Claim evidence upload failed",
            extra=build_log_extra(
                event="claim_evidence_uploaded_failed",
                route=_route(request),
                method=_method(request),
                status_code=500,
                file_name=file_name,
            ),
        )
        # `from None` keeps the upload error, which contains the file name, out of Sentry.
        raise HTTPException(
            status_code=500, detail="Failed to upload claim evidence"
        ) from None

    return UploadClaimEvidenceResponse(
        claim_evidence_id=claim_evidence_id,
        claim_evidence_file_name=file_name,
    )


@router.get(
    "/{claim_evidence_id}",
    response_class=StreamingResponse,
    responses={200: {"content": {"image/png": {}}}},
    dependencies=[
        Depends(
            require_permission_from([Permission.CLAIM_CREATE, Permission.CLAIM_READ])
        )
    ],
)
def retrieve_claim_evidence(
    claim_evidence_id: uuid.UUID,
    caller: Annotated[Caller, Depends(get_caller)],
    disposition: Literal["inline", "attachment"] = "inline",
    use_case: RetrieveClaimEvidenceUseCase = Depends(get_claim_evidence_use_case),
    request: Request = None,
) -> StreamingResponse:
    """Stream a piece of claim evidence, independent of whether it is linked to a claim yet."""
    try:
        result = use_case.execute(claim_evidence_id, caller)
    except ClaimEvidenceNotFoundError:
        logger.warning(
            "Claim evidence retrieval failed: not found",
            extra=build_log_extra(
                event="claim_evidence_retrieved_failed",
                route=_route(request),
                method=_method(request),
                status_code=404,
                claim_evidence_id=str(claim_evidence_id),
            ),
        )
        raise HTTPException(status_code=404, detail="Claim evidence not found")
    except ClaimEvidenceRetrievalError:
        logger.warning(
            "Claim evidence retrieval failed",
            extra=build_log_extra(
                event="claim_evidence_retrieved_failed",
                route=_route(request),
                method=_method(request),
                status_code=500,
                claim_evidence_id=str(claim_evidence_id),
            ),
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve claim evidence")

    mime_type = guess_type(result.file_name)
    supported_mime_types = [
        "image/png",
        "image/jpeg",
        "image/bmp",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    ]
    if mime_type[0] not in supported_mime_types:
        raise HTTPException(
            status_code=415,
            detail="Returned file type is not supported for streaming. Supported file types are: .png, .jpg, .jpeg, .bmp, .pdf, .xlsx, .xls",
        )

    return StreamingResponse(
        result.content,
        media_type=mime_type[0],
        headers={
            "Content-Disposition": content_disposition(disposition, result.file_name)
        },
    )


@router.get(
    "/{claim_reference}/application",
    response_model=ClaimApplicationResponse,
    dependencies=[Depends(require_permission_from(Permission.CLAIM_READ))],
)
def retrieve_application_for_claim(
    claim_reference: str,
    use_case: RetrieveApplicationForClaimUseCase = Depends(
        get_retrieve_application_for_claim_use_case
    ),
) -> ClaimApplicationResponse:
    try:
        laa_reference = use_case.execute(claim_reference)
        return ClaimApplicationResponse(laa_reference=laa_reference)
    except ClaimNotFoundError:
        raise HTTPException(status_code=404, detail="Claim not found")


@router.delete(
    "/{claim_evidence_id}",
    status_code=204,
    dependencies=[Depends(require_permission_from(Permission.CLAIM_CREATE))],
)
def delete_claim_evidence(
    claim_evidence_id: uuid.UUID,
    user_office_codes: Annotated[
        frozenset[str], Depends(get_current_provider_office_codes)
    ],
    use_case: DeleteClaimEvidenceUseCase = Depends(get_delete_claim_evidence_use_case),
    request: Request = None,
) -> Response:
    try:
        use_case.execute(claim_evidence_id, user_office_codes)
    except ClaimEvidenceNotFoundError:
        logger.warning(
            "Claim evidence delete failed: not found",
            extra=build_log_extra(
                event="claim_evidence_deleted_failed",
                route=_route(request),
                method=_method(request),
                status_code=404,
                claim_evidence_id=str(claim_evidence_id),
            ),
        )
        raise HTTPException(status_code=404, detail="Claim evidence not found")
    except ClaimEvidenceDeleteError:
        logger.warning(
            "Claim evidence delete failed",
            extra=build_log_extra(
                event="claim_evidence_deleted_failed",
                route=_route(request),
                method=_method(request),
                status_code=500,
                claim_evidence_id=str(claim_evidence_id),
            ),
        )
        raise HTTPException(status_code=500, detail="Failed to delete claim evidence")

    return Response(status_code=204)
