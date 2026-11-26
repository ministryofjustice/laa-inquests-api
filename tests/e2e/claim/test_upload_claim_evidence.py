import io
import json
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import api
from app.auth.rbac import Permission, Role, get_current_user_permissions
from app.models.claim.index import ClaimEvidence
from app.ports.sds_port import SdsPort
from app.routers.claims import get_sds_port
from app.routers.dependencies import get_current_provider_office_codes
from app.use_cases.exceptions import ClaimEvidenceUploadError
from tests.helpers.multipart import UNSAFE_FILE_NAMES, raw_file_upload
from tests.helpers.spreadsheet_files import (
    MACRO_SHEET_XLSX,
    MACRO_XLSX,
    OLE2_XLS,
    PLAIN_XLSX,
    XLSX_MIME_TYPE,
    build_zip,
)


def is_valid_uuid(val):
    try:
        uuid.UUID(val)
        return True
    except ValueError:
        return False


class TestUploadClaimEvidenceOfficeId:
    @pytest.mark.parametrize("office_id", ["0U651L", "1A234B"])
    @pytest.mark.parametrize(
        ("file_name", "content_type", "content"),
        [
            pytest.param(
                "poa_evidence.pdf", "application/pdf", b"test content", id="poa"
            ),
            pytest.param(
                "final_bill_evidence.pdf",
                "application/pdf",
                b"test content",
                id="final-bill",
            ),
            pytest.param(
                "cost_template.xlsx",
                XLSX_MIME_TYPE,
                PLAIN_XLSX,
                id="cost-template-xlsx",
            ),
        ],
    )
    def test_201_stores_uploading_office_without_changing_response(
        self,
        client: TestClient,
        session: Session,
        office_id: str,
        file_name: str,
        content_type: str,
        content: bytes,
    ) -> None:
        api.dependency_overrides[get_current_provider_office_codes] = lambda: frozenset(
            {"0U651L", "1A234B"}
        )

        response = client.post(
            "/claims/evidence",
            data={"office_id": office_id},
            files={"file": (file_name, io.BytesIO(content), content_type)},
            headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
        )

        assert response.status_code == 201
        body = response.json()
        evidence_id = uuid.UUID(body["claimEvidenceId"])
        assert body == {
            "claimEvidenceId": str(evidence_id),
            "claimEvidenceFileName": file_name,
        }
        evidence = session.get(ClaimEvidence, evidence_id)
        assert evidence is not None
        assert evidence.office_id == office_id
        assert evidence.claim_id is None
        assert evidence.file_size == len(content)

    @pytest.mark.parametrize(
        "office_id", [None, "", " ", "0U 651L", "0U651L<b>", "0U-651L", "A" * 21]
    )
    def test_422_requires_valid_office_without_side_effects(
        self, client: TestClient, session: Session, office_id: str | None
    ) -> None:
        mock_sds = MagicMock(spec=SdsPort)
        api.dependency_overrides[get_sds_port] = lambda: mock_sds
        evidence_ids_before = session.exec(
            select(ClaimEvidence.claim_evidence_id)
        ).all()

        response = client.post(
            "/claims/evidence",
            data={} if office_id is None else {"office_id": office_id},
            files={
                "file": ("evidence.pdf", io.BytesIO(b"test content"), "application/pdf")
            },
            headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
        )

        assert response.status_code == 422
        assert any(
            error["loc"] == ["body", "office_id"] for error in response.json()["detail"]
        )
        mock_sds.virus_check_claim_evidence.assert_not_called()
        mock_sds.save_claim_evidence.assert_not_called()
        assert (
            session.exec(select(ClaimEvidence.claim_evidence_id)).all()
            == evidence_ids_before
        )

    def test_403_rejects_another_office_without_side_effects(
        self, client: TestClient, session: Session
    ) -> None:
        mock_sds = MagicMock(spec=SdsPort)
        api.dependency_overrides[get_sds_port] = lambda: mock_sds
        evidence_ids_before = session.exec(
            select(ClaimEvidence.claim_evidence_id)
        ).all()

        response = client.post(
            "/claims/evidence",
            data={"office_id": "1A234B"},
            files={
                "file": ("evidence.pdf", io.BytesIO(b"test content"), "application/pdf")
            },
            headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
        )

        assert response.status_code == 403
        assert "1A234B" not in response.text
        assert "0U651L" not in response.text
        mock_sds.virus_check_claim_evidence.assert_not_called()
        mock_sds.save_claim_evidence.assert_not_called()
        assert (
            session.exec(select(ClaimEvidence.claim_evidence_id)).all()
            == evidence_ids_before
        )


def test_201_upload_claim_evidence_returns_claim_evidence_id(client):
    response = client.post(
        "/claims/evidence",
        data={"office_id": "0U651L"},
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
        data={"office_id": "0U651L"},
        files={"file": ("claim_evidence.pdf", io.BytesIO(content), "application/pdf")},
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )
    assert response.status_code == 201
    evidence = session.get(ClaimEvidence, uuid.UUID(response.json()["claimEvidenceId"]))
    assert evidence.file_size == len(content)


def test_201_upload_claim_evidence_accepts_xlsx(client):
    response = client.post(
        "/claims/evidence",
        data={"office_id": "0U651L"},
        files={
            "file": (
                "claim_cost_template.xlsx",
                io.BytesIO(PLAIN_XLSX),
                XLSX_MIME_TYPE,
            )
        },
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "claimEvidenceId" in body
    assert is_valid_uuid(body["claimEvidenceId"])


def _upload_spreadsheet(client, file_name, content, mime_type=XLSX_MIME_TYPE):
    return client.post(
        "/claims/evidence",
        data={"office_id": "0U651L"},
        files={"file": (file_name, io.BytesIO(content), mime_type)},
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )


@pytest.mark.parametrize(
    ("file_name", "content", "mime_type", "expected_code"),
    [
        pytest.param(
            "claim_cost_template.xlsx",
            MACRO_XLSX,
            XLSX_MIME_TYPE,
            "MACROS_NOT_ALLOWED",
            id="macro_workbook_declared_as_xlsx",
        ),
        pytest.param(
            "claim_cost_template.xlsx",
            MACRO_SHEET_XLSX,
            XLSX_MIME_TYPE,
            "MACROS_NOT_ALLOWED",
            id="excel_4_macro_sheet",
        ),
        pytest.param(
            "claim_cost_template.xlsm",
            MACRO_XLSX,
            "application/vnd.ms-excel.sheet.macroEnabled.12",
            "UNSUPPORTED_FILE_TYPE",
            id="xlsm_extension",
        ),
        pytest.param(
            "claim_cost_template.xls",
            OLE2_XLS,
            "application/vnd.ms-excel",
            "UNSUPPORTED_FILE_TYPE",
            id="xls_extension",
        ),
        pytest.param(
            "claim_evidence.pdf",
            MACRO_XLSX,
            "application/pdf",
            "CONTENT_MISMATCH",
            id="macro_workbook_renamed_to_pdf",
        ),
        pytest.param(
            "claim_cost_template.xlsx",
            b"test content",
            XLSX_MIME_TYPE,
            "CONTENT_MISMATCH",
            id="xlsx_name_with_non_zip_content",
        ),
        pytest.param(
            "claim_cost_template.xlsx",
            build_zip((("readme.txt", b"not a workbook"),)),
            XLSX_MIME_TYPE,
            "INVALID_SPREADSHEET",
            id="zip_that_is_not_a_workbook",
        ),
    ],
)
def test_422_upload_claim_evidence_rejects_unsafe_spreadsheet(
    client, file_name, content, mime_type, expected_code
):
    response = _upload_spreadsheet(client, file_name, content, mime_type)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == expected_code
    assert detail["message"]


def test_422_rejected_spreadsheet_is_not_sent_to_sds(client):
    mock_sds = MagicMock()
    api.dependency_overrides[get_sds_port] = lambda: mock_sds

    response = _upload_spreadsheet(client, "claim_cost_template.xlsx", MACRO_XLSX)

    assert response.status_code == 422
    mock_sds.virus_check_claim_evidence.assert_not_called()
    mock_sds.save_claim_evidence.assert_not_called()


def test_422_rejected_spreadsheet_is_not_stored(client, session):
    evidence_count_before = len(session.exec(select(ClaimEvidence)).all())

    response = _upload_spreadsheet(client, "claim_cost_template.xlsx", MACRO_XLSX)

    assert response.status_code == 422
    assert len(session.exec(select(ClaimEvidence)).all()) == evidence_count_before


def test_422_upload_claim_evidence_with_no_file(client):
    response = client.post(
        "/claims/evidence",
        data={"office_id": "0U651L"},
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
        data={"office_id": "0U651L"},
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
        data={"office_id": "0U651L"},
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
        data={"office_id": "0U651L"},
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
        data={"office_id": "0U651L"},
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


class TestUploadClaimEvidenceFileName:
    @pytest.mark.parametrize("file_name", UNSAFE_FILE_NAMES)
    def test_422_upload_claim_evidence_with_unsafe_file_name(
        self, client, session, file_name
    ):
        mock_sds = MagicMock()
        api.dependency_overrides[get_sds_port] = lambda: mock_sds

        response = raw_file_upload(
            client,
            "/claims/evidence",
            file_name,
            {"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
            fields={"office_id": "0U651L"},
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "Invalid file name"
        mock_sds.virus_check_claim_evidence.assert_not_called()
        mock_sds.save_claim_evidence.assert_not_called()
        assert session.exec(select(ClaimEvidence)).all() == []

    @pytest.mark.parametrize(
        "file_name",
        ["claim_evidence.pdf", "Evidence (1).pdf", "Jane Doe - invoice_2024.pdf"],
    )
    def test_201_upload_claim_evidence_with_normal_file_name(self, client, file_name):
        response = raw_file_upload(
            client,
            "/claims/evidence",
            file_name,
            {"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
            fields={"office_id": "0U651L"},
        )

        assert response.status_code == 201


class TestUploadClaimEvidenceRbac:
    def test_201_upload_claim_evidence_with_provider_claims_user_app_role(self, client):
        response = client.post(
            "/claims/evidence",
            data={"office_id": "0U651L"},
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
            data={"office_id": "0U651L"},
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
            data={"office_id": "0U651L"},
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
        assert len(captured_sentry_events) >= 1
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
        assert len(captured_sentry_events) >= 1
        assert "Jane" not in json.dumps(captured_sentry_events)
        assert "passport" not in json.dumps(captured_sentry_events)

    def test_422_virus_detected_sends_event_without_file_name_to_sentry(
        self, client, captured_sentry_events
    ):
        mock_sds = MagicMock()
        mock_sds.virus_check_claim_evidence.return_value = False
        api.dependency_overrides[get_sds_port] = lambda: mock_sds

        response = self._upload(client)

        assert response.status_code == 422
        assert len(captured_sentry_events) >= 1
        assert "Jane" not in json.dumps(captured_sentry_events)
        assert "passport" not in json.dumps(captured_sentry_events)

    def test_422_rejected_spreadsheet_does_not_send_file_name_to_sentry_or_response(
        self, client, captured_sentry_events
    ):
        response = client.post(
            "/claims/evidence",
            data={"office_id": "0U651L"},
            files={
                "file": (
                    "Jane Doe passport.xlsx",
                    io.BytesIO(MACRO_XLSX),
                    XLSX_MIME_TYPE,
                )
            },
            headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
        )

        assert response.status_code == 422
        assert "Jane" not in response.text
        assert "Jane" not in json.dumps(captured_sentry_events)
        assert "passport" not in json.dumps(captured_sentry_events)
