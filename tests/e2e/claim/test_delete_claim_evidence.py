import io
import json
import uuid
from unittest.mock import MagicMock

import pytest

from app import api
from app.auth.rbac import Permission, Role, get_current_user_permissions
from app.models.claim.enums import ClaimType
from app.models.claim.index import ClaimCostTemplate, ClaimEvidence
from app.routers.claims import get_sds_port
from app.use_cases.exceptions import ClaimEvidenceDeleteError
from tests.e2e.auth import set_token_office_codes
from tests.e2e.factories import (
    create_application_in_db,
    create_claim_evidence_in_db,
    create_claim_in_db,
)


def _upload_evidence_and_get_id(client, auth_token):
    upload_response = client.post(
        "/claims/evidence",
        data={"office_id": "0U651L"},
        files={
            "file": (
                "claim_evidence.pdf",
                io.BytesIO(b"test content"),
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert upload_response.status_code == 201
    return upload_response.json()["claimEvidenceId"]


def test_204_delete_claim_evidence(client):
    claim_evidence_id = _upload_evidence_and_get_id(
        client, Role.PROVIDER_CLAIMS_USER.value
    )

    delete_response = client.delete(
        f"/claims/{claim_evidence_id}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert delete_response.status_code == 204


def test_404_delete_claim_evidence_when_unknown_id(client):
    delete_response = client.delete(
        "/claims/00000000-0000-0000-0000-000000000001",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert delete_response.status_code == 404


def test_500_delete_claim_evidence_when_sds_fails(client):
    claim_evidence_id = _upload_evidence_and_get_id(
        client, Role.PROVIDER_CLAIMS_USER.value
    )

    def get_sds_port_override_with_delete_error():
        mock_sds = MagicMock()
        mock_sds.delete_claim_evidence.side_effect = Exception("SDS delete failed")
        return mock_sds

    api.dependency_overrides[get_sds_port] = get_sds_port_override_with_delete_error

    delete_response = client.delete(
        f"/claims/{claim_evidence_id}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert delete_response.status_code == 500


class TestDeleteClaimEvidenceRbac:
    def test_204_delete_claim_evidence_with_provider_claims_user_app_role(
        self, session, client
    ):
        claim_evidence = ClaimEvidence(
            sds_file_name="stored-claim-evidence_abc123.pdf",
            file_name="claim_evidence.pdf",
            office_id="0U651L",
        )
        session.add(claim_evidence)
        session.commit()
        session.refresh(claim_evidence)

        response = client.delete(
            f"/claims/{claim_evidence.claim_evidence_id}",
            headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
        )

        assert response.status_code == 204


class TestDeleteClaimEvidenceOfficeIdCheck:
    @pytest.fixture
    def sds_files(self, client):
        files = {"stored-file-key": b"file bytes"}
        sds = MagicMock()
        sds.delete_claim_evidence.side_effect = lambda key: files.pop(key)
        api.dependency_overrides[get_sds_port] = lambda: sds
        return files, sds

    @staticmethod
    def _create_file(session, file_type, office_id, firm_code):
        application = create_application_in_db(
            session,
            provider_overrides={"firm_code": firm_code, "office_id": office_id},
        )
        claim = create_claim_in_db(
            session,
            application_id=application.application_id,
            claim_type=(
                ClaimType.PAYMENT_ON_ACCOUNT
                if file_type == "poa_evidence"
                else ClaimType.FINAL_BILL
            ),
        )
        evidence = create_claim_evidence_in_db(
            session,
            office_id=office_id,
            sds_file_name="stored-file-key",
            claim_id=claim.claim_id if file_type != "cost_template" else None,
        )
        if file_type == "cost_template":
            session.add(
                ClaimCostTemplate(
                    claim_id=claim.claim_id,
                    claim_cost_template_file_id=evidence.claim_evidence_id,
                    claim_cost_template_file_name="cost-template.xlsx",
                )
            )
            session.commit()
        return evidence

    @pytest.mark.parametrize(
        "file_type", ["poa_evidence", "final_bill_evidence", "cost_template"]
    )
    @pytest.mark.parametrize(
        ("file_office", "token_offices"),
        [
            ("0U651L", {"0U651L"}),
            ("002", {"0U651L", "002"}),
        ],
        ids=["own-office", "second-office-in-token"],
    )
    def test_204_deletes_file_when_its_office_id_is_in_the_token(
        self, session, client, sds_files, file_type, file_office, token_offices
    ):
        set_token_office_codes(token_offices)
        evidence = self._create_file(session, file_type, file_office, "0A123B")
        evidence_id = evidence.claim_evidence_id
        files, sds = sds_files

        response = client.delete(
            f"/claims/{evidence_id}",
            headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
        )

        assert response.status_code == 204
        assert session.get(ClaimEvidence, evidence_id) is None
        assert "stored-file-key" not in files
        sds.delete_claim_evidence.assert_called_once_with("stored-file-key")

    @pytest.mark.parametrize(
        "file_type", ["poa_evidence", "final_bill_evidence", "cost_template"]
    )
    @pytest.mark.parametrize(
        ("firm_code", "file_office"),
        [("0A123B", "002"), ("ZZ999Z", "003")],
        ids=["same-firm-different-office", "different-firm"],
    )
    def test_404_does_not_delete_file_when_its_office_id_is_not_in_the_token(
        self, session, client, sds_files, file_type, firm_code, file_office
    ):
        set_token_office_codes({"0U651L"})
        evidence = self._create_file(session, file_type, file_office, firm_code)
        evidence_id = evidence.claim_evidence_id
        existing_claim_id = evidence.claim_id
        files, sds = sds_files
        headers = {"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"}

        unknown_response = client.delete(f"/claims/{uuid.uuid4()}", headers=headers)
        response = client.delete(f"/claims/{evidence_id}", headers=headers)

        assert response.status_code == unknown_response.status_code == 404
        assert response.json() == unknown_response.json()
        session.expire_all()
        stored = session.get(ClaimEvidence, evidence_id)
        assert stored is not None
        assert stored.claim_id == existing_claim_id
        assert files["stored-file-key"] == b"file bytes"
        sds.delete_claim_evidence.assert_not_called()

    def test_403_non_provider_cannot_delete_evidence_even_with_create_permission(
        self, session, client, sds_files
    ):
        evidence = self._create_file(session, "poa_evidence", "0U651L", "0A123B")
        evidence_id = evidence.claim_evidence_id
        files, sds = sds_files
        api.dependency_overrides[get_current_user_permissions] = lambda: {
            Permission.CLAIM_CREATE
        }

        response = client.delete(
            f"/claims/{evidence_id}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 403
        session.expire_all()
        assert session.get(ClaimEvidence, evidence_id) is not None
        assert files["stored-file-key"] == b"file bytes"
        sds.delete_claim_evidence.assert_not_called()


def test_500_delete_claim_evidence_failure_does_not_send_sds_file_key_to_sentry(
    client, captured_sentry_events
):
    claim_evidence_id = _upload_evidence_and_get_id(
        client, Role.PROVIDER_CLAIMS_USER.value
    )
    mock_sds = MagicMock()
    mock_sds.delete_claim_evidence.side_effect = ClaimEvidenceDeleteError(
        "SDS returned 500 while deleting claim evidence for file key Jane_Doe_passport_3f2b8c1e.pdf"
    )
    api.dependency_overrides[get_sds_port] = lambda: mock_sds

    response = client.delete(
        f"/claims/{claim_evidence_id}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 500
    assert len(captured_sentry_events) >= 1
    assert "Jane" not in json.dumps(captured_sentry_events)
    assert "passport" not in json.dumps(captured_sentry_events)
