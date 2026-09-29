import uuid

from app.adapters.claim_repository_adapter import ClaimRepositoryAdapter
from tests.factories.persisted import create_claim_evidence


def test_get_claim_evidence_by_id_returns_domain_claim_evidence_when_found(session):
    claim_evidence = create_claim_evidence(
        session,
        sds_file_name="stored-claim-evidence_abc123.pdf",
        file_name="claim_evidence.pdf",
    )

    adapter = ClaimRepositoryAdapter(session)

    result = adapter.get_claim_evidence_by_id(claim_evidence.claim_evidence_id)

    assert result is not None
    assert result.sds_file_name == "stored-claim-evidence_abc123.pdf"
    assert result.file_name == "claim_evidence.pdf"


def test_get_claim_evidence_by_id_returns_none_when_not_found(session):
    adapter = ClaimRepositoryAdapter(session)

    result = adapter.get_claim_evidence_by_id(uuid.uuid4())

    assert result is None
