import uuid

from app.adapters.claim_repository_adapter import ClaimRepositoryAdapter
from app.domain.claim_evidence import ClaimEvidence
from app.models.claim.index import ClaimEvidence as ClaimEvidenceModel

SDS_FILE_NAME = "stored-claim-evidence_abc123.pdf"
FILE_NAME = "claim_evidence.pdf"
OFFICE_ID = "1A234B"


class TestSaveUploadedClaimEvidence:
    def test_stores_office_id(self, session):
        adapter = ClaimRepositoryAdapter(session)

        claim_evidence_id = adapter.save_uploaded_claim_evidence(
            ClaimEvidence(
                sds_file_name=SDS_FILE_NAME,
                file_name=FILE_NAME,
                office_id=OFFICE_ID,
                file_size=4,
            )
        )

        saved = session.get(ClaimEvidenceModel, claim_evidence_id)
        assert saved.office_id == OFFICE_ID


class TestGetClaimEvidenceById:
    def test_returns_domain_claim_evidence_when_found(self, session):
        claim_evidence = ClaimEvidenceModel(
            sds_file_name=SDS_FILE_NAME,
            file_name=FILE_NAME,
            office_id=OFFICE_ID,
        )
        session.add(claim_evidence)
        session.commit()
        session.refresh(claim_evidence)

        adapter = ClaimRepositoryAdapter(session)

        result = adapter.get_claim_evidence_by_id(claim_evidence.claim_evidence_id)

        assert result == ClaimEvidence(
            sds_file_name=SDS_FILE_NAME,
            file_name=FILE_NAME,
            office_id=OFFICE_ID,
        )

    def test_returns_none_when_not_found(self, session):
        adapter = ClaimRepositoryAdapter(session)

        result = adapter.get_claim_evidence_by_id(uuid.uuid4())

        assert result is None
