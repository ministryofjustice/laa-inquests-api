import uuid

import pytest

from app.adapters.claim_repository_adapter import ClaimRepositoryAdapter
from app.models.claim.index import ClaimEvidence
from tests.e2e.factories import create_claim_evidence_in_db
from tests.unit.factories import create_base_claim_evidence_domain


@pytest.fixture
def adapter(session):
    return ClaimRepositoryAdapter(session)


class TestSaveUploadedClaimEvidence:
    def test_stores_office_id(self, session, adapter):
        claim_evidence_id = adapter.save_uploaded_claim_evidence(
            create_base_claim_evidence_domain(office_id="1A234B")
        )

        saved = session.get(ClaimEvidence, claim_evidence_id)
        assert saved.office_id == "1A234B"


class TestGetClaimEvidenceById:
    def test_returns_domain_claim_evidence_when_found(self, session, adapter):
        stored = create_claim_evidence_in_db(session, office_id="1A234B")

        result = adapter.get_claim_evidence_by_id(stored.claim_evidence_id)

        assert result == create_base_claim_evidence_domain(office_id="1A234B")

    def test_returns_none_when_not_found(self, adapter):
        assert adapter.get_claim_evidence_by_id(uuid.uuid4()) is None
