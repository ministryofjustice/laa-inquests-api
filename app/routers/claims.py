import uuid
from mimetypes import guess_type
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.models.claim.index import UploadClaimEvidenceResponse
from app.ports.claim.get_claim_evidence_port import GetClaimEvidencePort
from app.ports.claim.upload_claim_evidence_port import UploadClaimEvidencePort
from app.ports.sds_port import SdsPort
from app.routers.dependencies import (
    get_claim_db_adapter,
    get_sds_port,
    verify_entra_provider_token,
)
from app.use_cases.exceptions import (
    ClaimEvidenceNotFoundError,
    ClaimEvidenceRetrievalError,
    ClaimEvidenceUploadError,
    ClaimEvidenceVirusDetectedError,
)
from app.use_cases.retrieve_claim_evidence import RetrieveClaimEvidenceUseCase
from app.use_cases.upload_claim_evidence import UploadClaimEvidenceUseCase

router = APIRouter(
    prefix="/claims",
    tags=["Claims"],
    responses={404: {"description": "Not found"}},
)


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


@router.post(
    "/evidence",
    response_model=UploadClaimEvidenceResponse,
    status_code=201,
)
async def upload_claim_evidence(
    file: UploadFile = File(...),
    use_case: UploadClaimEvidenceUseCase = Depends(get_upload_claim_evidence_use_case),
    _: None = Depends(verify_entra_provider_token),
) -> UploadClaimEvidenceResponse:
    """Upload claim evidence to document storage and return its file ID."""
    contents = await file.read()
    file_name = file.filename
    try:
        claim_evidence_id = use_case.execute(
            contents,
            file_name,
        )
    except ClaimEvidenceVirusDetectedError:
        raise HTTPException(status_code=422, detail="Uploaded file failed virus check")
    except ClaimEvidenceUploadError:
        raise HTTPException(status_code=500, detail="Failed to upload claim evidence")

    return UploadClaimEvidenceResponse(
        claim_evidence_id=claim_evidence_id,
        claim_evidence_file_name=file_name,
    )


@router.get(
    "/{claim_evidence_id}",
    response_class=StreamingResponse,
    responses={200: {"content": {"image/png": {}}}},
)
def retrieve_claim_evidence(
    claim_evidence_id: uuid.UUID,
    disposition: Literal["inline", "attachment"] = "inline",
    use_case: RetrieveClaimEvidenceUseCase = Depends(get_claim_evidence_use_case),
    _: None = Depends(verify_entra_provider_token),
) -> StreamingResponse:
    """Stream a piece of claim evidence, independent of whether it is linked to a claim yet."""
    try:
        result = use_case.execute(claim_evidence_id)
    except ClaimEvidenceNotFoundError:
        raise HTTPException(status_code=404, detail="Claim evidence not found")
    except ClaimEvidenceRetrievalError:
        raise HTTPException(status_code=500, detail="Failed to retrieve claim evidence")

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
        headers={
            "Content-Disposition": f'{disposition}; filename="{result.file_name}"'
        },
    )
