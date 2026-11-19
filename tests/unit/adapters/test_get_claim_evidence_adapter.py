import uuid

from app.adapters.claim_repository_adapter import ClaimRepositoryAdapter
from app.domain.claim_evidence import ClaimEvidence as DomainClaimEvidence
from app.models.claim.index import ClaimEvidence


def test_get_claim_evidence_by_id_returns_domain_claim_evidence_when_found(session):
    claim_evidence = ClaimEvidence(
        sds_file_name="stored-claim-evidence_abc123.pdf",
        file_name="claim_evidence.pdf",
        office_id="1A234B",
    )
    session.add(claim_evidence)
    session.commit()
    session.refresh(claim_evidence)

    adapter = ClaimRepositoryAdapter(session)

    result = adapter.get_claim_evidence_by_id(claim_evidence.claim_evidence_id)

    assert result is not None
    assert result.sds_file_name == "stored-claim-evidence_abc123.pdf"
    assert result.file_name == "claim_evidence.pdf"
    assert result.office_id == "1A234B"


def test_get_claim_evidence_by_id_returns_none_when_not_found(session):
    adapter = ClaimRepositoryAdapter(session)

    result = adapter.get_claim_evidence_by_id(uuid.uuid4())

    assert result is None


def test_save_uploaded_claim_evidence_stores_office_id(session):
    adapter = ClaimRepositoryAdapter(session)

    claim_evidence_id = adapter.save_uploaded_claim_evidence(
        DomainClaimEvidence(
            sds_file_name="stored-claim-evidence_abc123.pdf",
            file_name="claim_evidence.pdf",
            office_id="1A234B",
            file_size=4,
        )
    )

    saved = session.get(ClaimEvidence, claim_evidence_id)
    assert saved.office_id == "1A234B"
