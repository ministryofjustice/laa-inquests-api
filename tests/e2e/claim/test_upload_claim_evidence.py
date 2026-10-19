import io
import json
import uuid
from unittest.mock import MagicMock

from app import api
from app.auth.rbac import Permission, Role, get_current_user_permissions
from app.models.claim.index import ClaimEvidence
from app.routers.claims import get_sds_port
from app.use_cases.exceptions import ClaimEvidenceUploadError


def is_valid_uuid(val):
    try:
        uuid.UUID(val)
        return True
    except ValueError:
        return False


def test_201_upload_claim_evidence_returns_claim_evidence_id(client):
    response = client.post(
        "/claims/evidence",
        files={
            "file": (
                "claim_evidence.pdf",
                io.BytesIO(b"test content"),
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "claimEvidenceId" in body
    assert is_valid_uuid(body["claimEvidenceId"])


def test_201_upload_claim_evidence_stores_file_size(client, session):
    content = b"test content"
    response = client.post(
        "/claims/evidence",
        files={"file": ("claim_evidence.pdf", io.BytesIO(content), "application/pdf")},
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )
    assert response.status_code == 201
    evidence = session.get(ClaimEvidence, uuid.UUID(response.json()["claimEvidenceId"]))
    assert evidence.file_size == len(content)


def test_201_upload_claim_evidence_accepts_xlsx(client):
    response = client.post(
        "/claims/evidence",
        files={
            "file": (
                "claim_cost_template.xlsx",
                io.BytesIO(b"test content"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "claimEvidenceId" in body
    assert is_valid_uuid(body["claimEvidenceId"])


def test_201_upload_claim_evidence_accepts_xls(client):
    response = client.post(
        "/claims/evidence",
        files={
            "file": (
                "claim_cost_template.xls",
                io.BytesIO(b"test content"),
                "application/vnd.ms-excel",
            )
        },
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "claimEvidenceId" in body
    assert is_valid_uuid(body["claimEvidenceId"])


def test_422_upload_claim_evidence_with_no_file(client):
    response = client.post(
        "/claims/evidence",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )
    assert response.status_code == 422


def test_422_upload_claim_evidence_with_failed_virus_check(client):
    def get_sds_port_override_with_failed_virus_check():
        mock_sds = MagicMock()
        mock_sds.virus_check_claim_evidence.return_value = False
        return mock_sds

    api.dependency_overrides[get_sds_port] = (
        get_sds_port_override_with_failed_virus_check
    )

    response = client.post(
        "/claims/evidence",
        files={
            "file": (
                "claim_evidence.pdf",
                io.BytesIO(b"test content"),
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )
    assert response.status_code == 422


def test_500_upload_claim_evidence_with_sds_server_error(client):
    def get_sds_port_override_with_server_error():
        mock_sds = MagicMock()
        mock_sds.virus_check_claim_evidence.side_effect = Exception("SDS server error")
        return mock_sds

    api.dependency_overrides[get_sds_port] = get_sds_port_override_with_server_error

    response = client.post(
        "/claims/evidence",
        files={
            "file": (
                "claim_evidence.pdf",
                io.BytesIO(b"test content"),
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )
    assert response.status_code == 500


def test_201_upload_claim_evidence_allows_multiple_uploads(client):
    first = client.post(
        "/claims/evidence",
        files={
            "file": (
                "claim_evidence_1.pdf",
                io.BytesIO(b"test content 1"),
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )
    second = client.post(
        "/claims/evidence",
        files={
            "file": (
                "claim_evidence_2.pdf",
                io.BytesIO(b"test content 2"),
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert first.status_code == 201
    assert second.status_code == 201

    first_body = first.json()
    second_body = second.json()

    assert "claimEvidenceId" in first_body
    assert "claimEvidenceId" in second_body


class TestUploadClaimEvidenceRbac:
    def test_201_upload_claim_evidence_with_provider_claims_user_app_role(self, client):
        response = client.post(
            "/claims/evidence",
            files={
                "file": (
                    "claim_evidence.pdf",
                    io.BytesIO(b"test content"),
                    "application/pdf",
                )
            },
            headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
        )

        assert response.status_code == 201

    def test_201_upload_claim_evidence_with_upload_permission(self, client):
        def get_current_user_permissions_override():
            return {Permission.CLAIM_CREATE}

        api.dependency_overrides[get_current_user_permissions] = (
            get_current_user_permissions_override
        )

        response = client.post(
            "/claims/evidence",
            files={
                "file": (
                    "claim_evidence.pdf",
                    io.BytesIO(b"test content"),
                    "application/pdf",
                )
            },
            headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
        )

        assert response.status_code == 201


PII_FILE_NAME = "Jane Doe passport.pdf"


class TestUploadClaimEvidenceSentryPii:
    def _upload(self, client):
        return client.post(
            "/claims/evidence",
            files={
                "file": (PII_FILE_NAME, io.BytesIO(b"test content"), "application/pdf")
            },
            headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
        )

    def test_500_virus_check_failure_does_not_send_file_name_to_sentry(
        self, client, captured_sentry_events
    ):
        mock_sds = MagicMock()
        mock_sds.virus_check_claim_evidence.side_effect = ClaimEvidenceUploadError(
            "Failed to perform virus check due to a network error: "
            "https://sds/virus_check_file?file_key=Jane+Doe+passport.pdf"
        )
        api.dependency_overrides[get_sds_port] = lambda: mock_sds

        response = self._upload(client)

        assert response.status_code == 500
        assert len(captured_sentry_events) == 1
        assert "Jane" not in json.dumps(captured_sentry_events)
        assert "passport" not in json.dumps(captured_sentry_events)

    def test_500_upload_not_successful_does_not_send_file_name_to_sentry(
        self, client, captured_sentry_events
    ):
        mock_sds = MagicMock()
        mock_sds.virus_check_claim_evidence.return_value = True
        mock_sds.save_claim_evidence.return_value.status = "FAILED"
        api.dependency_overrides[get_sds_port] = lambda: mock_sds

        response = self._upload(client)

        assert response.status_code == 500
        assert len(captured_sentry_events) == 1
        assert "Jane" not in json.dumps(captured_sentry_events)
        assert "passport" not in json.dumps(captured_sentry_events)
