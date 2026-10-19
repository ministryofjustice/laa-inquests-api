import json
import uuid
from unittest.mock import MagicMock

from sqlmodel import select

from app import api
from app.auth.rbac import Role
from app.models.application.index import Application
from app.models.claim.index import Claim, ClaimEvidence
from app.routers.claims import get_sds_port
from app.use_cases.exceptions import SDSClaimEvidenceRetrievalError


def _create_claim_evidence(session, claim_id: int | None = None) -> ClaimEvidence:
    claim_evidence = ClaimEvidence(
        sds_file_name="stored-claim-evidence_abc123.pdf",
        file_name="claim_evidence.pdf",
        claim_id=claim_id,
    )
    session.add(claim_evidence)
    session.commit()
    session.refresh(claim_evidence)
    return claim_evidence


def test_200_retrieve_claim_evidence_returns_file_content_before_claim_exists(
    session, client
):
    claim_evidence = _create_claim_evidence(session)

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 200
    assert response.content == b"file bytes"


def test_200_retrieve_claim_evidence_defaults_to_inline_disposition(session, client):
    claim_evidence = _create_claim_evidence(session)

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 200
    assert (
        response.headers["content-disposition"]
        == 'inline; filename="claim_evidence.pdf"'
    )


def test_200_retrieve_claim_evidence_supports_attachment_disposition(session, client):
    claim_evidence = _create_claim_evidence(session)

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        params={"disposition": "attachment"},
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 200
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="claim_evidence.pdf"'
    )


def test_200_retrieve_claim_evidence_returns_file_content_after_linked_to_claim(
    session, client
):
    application = session.exec(select(Application)).first()
    claim = Claim(
        application_id=application.application_id,
        claim_type_id="PAYMENT_ON_ACCOUNT",
        claim_reference=f"INQC-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}",
    )
    session.add(claim)
    session.commit()
    session.refresh(claim)
    claim_evidence = _create_claim_evidence(session, claim_id=claim.claim_id)

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 200
    assert response.content == b"file bytes"


def test_200_retrieve_claim_evidence_returns_xlsx_content(session, client):
    claim_evidence = ClaimEvidence(
        sds_file_name="stored-claim-evidence_abc123.xlsx",
        file_name="claim_cost_template.xlsx",
    )
    session.add(claim_evidence)
    session.commit()
    session.refresh(claim_evidence)

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 200
    assert response.content == b"file bytes"
    assert (
        response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert (
        response.headers["content-disposition"]
        == 'inline; filename="claim_cost_template.xlsx"'
    )


def test_200_retrieve_claim_evidence_returns_xls_content(session, client):
    claim_evidence = ClaimEvidence(
        sds_file_name="stored-claim-evidence_abc123.xls",
        file_name="claim_cost_template.xls",
    )
    session.add(claim_evidence)
    session.commit()
    session.refresh(claim_evidence)

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 200
    assert response.content == b"file bytes"
    assert response.headers["content-type"] == "application/vnd.ms-excel"
    assert (
        response.headers["content-disposition"]
        == 'inline; filename="claim_cost_template.xls"'
    )


def test_404_retrieve_claim_evidence_returns_404_when_not_found(client):
    response = client.get(
        f"/claims/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 404


def test_415_retrieve_claim_evidence_returns_415_for_unsupported_mime_type(
    session, client
):
    claim_evidence = ClaimEvidence(
        sds_file_name="stored-claim-evidence_abc123.exe",
        file_name="claim_evidence.exe",
    )
    session.add(claim_evidence)
    session.commit()
    session.refresh(claim_evidence)

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 415


def test_500_retrieve_claim_evidence_failure_does_not_send_sds_file_key_to_sentry(
    session, client, captured_sentry_events
):
    claim_evidence = _create_claim_evidence(session)
    mock_sds = MagicMock()
    mock_sds.retrieve_claim_evidence.side_effect = SDSClaimEvidenceRetrievalError(
        "SDS returned 404 while retrieving claim evidence for file key Jane_Doe_passport_3f2b8c1e.pdf"
    )
    api.dependency_overrides[get_sds_port] = lambda: mock_sds

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 500
    assert len(captured_sentry_events) >= 1
    assert "Jane" not in json.dumps(captured_sentry_events)
    assert "passport" not in json.dumps(captured_sentry_events)
