import uuid

from app.auth.rbac import Role
from tests.factories.persisted import create_claim, create_claim_evidence


def test_200_retrieve_claim_evidence_returns_file_content_before_claim_exists(
    session, client
):
    claim_evidence = create_claim_evidence(session)

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 200
    assert response.content == b"file bytes"


def test_200_retrieve_claim_evidence_defaults_to_inline_disposition(session, client):
    claim_evidence = create_claim_evidence(session, file_name="claim_evidence.pdf")

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
    claim_evidence = create_claim_evidence(session, file_name="claim_evidence.pdf")

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
    session, client, seeded_application
):
    application = seeded_application
    claim = create_claim(session, application)
    claim_evidence = create_claim_evidence(session, claim)

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 200
    assert response.content == b"file bytes"


def test_200_retrieve_claim_evidence_returns_xlsx_content(session, client):
    claim_evidence = create_claim_evidence(
        session,
        sds_file_name="stored-claim-evidence_abc123.xlsx",
        file_name="claim_cost_template.xlsx",
    )

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
    claim_evidence = create_claim_evidence(
        session,
        sds_file_name="stored-claim-evidence_abc123.xls",
        file_name="claim_cost_template.xls",
    )

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
    claim_evidence = create_claim_evidence(
        session,
        sds_file_name="stored-claim-evidence_abc123.exe",
        file_name="claim_evidence.exe",
    )

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 415
