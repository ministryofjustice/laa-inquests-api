import uuid

from sqlmodel import select

from app.models.application.index import Application
from app.models.claim.index import Claim, ClaimEvidence


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
    session, client, auth_token
):
    claim_evidence = _create_claim_evidence(session)

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.content == b"file bytes"


def test_200_retrieve_claim_evidence_defaults_to_inline_disposition(
    session, client, auth_token
):
    claim_evidence = _create_claim_evidence(session)

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert (
        response.headers["content-disposition"]
        == 'inline; filename="claim_evidence.pdf"'
    )


def test_200_retrieve_claim_evidence_supports_attachment_disposition(
    session, client, auth_token
):
    claim_evidence = _create_claim_evidence(session)

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        params={"disposition": "attachment"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="claim_evidence.pdf"'
    )


def test_200_retrieve_claim_evidence_returns_file_content_after_linked_to_claim(
    session, client, auth_token
):
    application = session.exec(select(Application)).first()
    claim = Claim(
        application_id=application.application_id,
        claim_type_id="PAYMENT_ON_ACCOUNT",
    )
    session.add(claim)
    session.commit()
    session.refresh(claim)
    claim_evidence = _create_claim_evidence(session, claim_id=claim.claim_id)

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.content == b"file bytes"


def test_200_retrieve_claim_evidence_returns_xlsx_content(session, client, auth_token):
    claim_evidence = ClaimEvidence(
        sds_file_name="stored-claim-evidence_abc123.xlsx",
        file_name="claim_cost_template.xlsx",
    )
    session.add(claim_evidence)
    session.commit()
    session.refresh(claim_evidence)

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
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


def test_200_retrieve_claim_evidence_returns_xls_content(session, client, auth_token):
    claim_evidence = ClaimEvidence(
        sds_file_name="stored-claim-evidence_abc123.xls",
        file_name="claim_cost_template.xls",
    )
    session.add(claim_evidence)
    session.commit()
    session.refresh(claim_evidence)

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.content == b"file bytes"
    assert response.headers["content-type"] == "application/vnd.ms-excel"
    assert (
        response.headers["content-disposition"]
        == 'inline; filename="claim_cost_template.xls"'
    )


def test_404_retrieve_claim_evidence_returns_404_when_not_found(client, auth_token):
    response = client.get(
        f"/claims/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 404


def test_415_retrieve_claim_evidence_returns_415_for_unsupported_mime_type(
    session, client, auth_token
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
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 415
