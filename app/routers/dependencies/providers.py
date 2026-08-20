from fastapi import Depends
from sqlmodel import Session

from app.adapters.claim_repository_adapter import ClaimRepositoryAdapter
from app.adapters.sds_adapter import SdsAdapter
from app.config import Config
from app.db import get_session
from app.ports.sds_port import SdsPort


def get_sds_port() -> SdsPort:
    return SdsAdapter(
        base_url=Config.SDS_BASE_URL,
        tenant_id=Config.SDS_TENANT_ID,
        client_id=Config.SDS_CLIENT_ID,
        client_secret=Config.SDS_CLIENT_SECRET,
        scope=Config.SDS_SCOPE,
    )


def get_claim_db_adapter(
    session: Session = Depends(get_session),
) -> ClaimRepositoryAdapter:
    return ClaimRepositoryAdapter(session=session)
