import json
import uuid
from unittest.mock import MagicMock

import pytest
from sqlmodel import select

from app import api
from app.auth.rbac import Role
from app.models.application.index import Application
from app.models.claim.enums import ClaimType
from app.models.claim.index import Claim, ClaimCostTemplate, ClaimEvidence
from app.routers.claims import get_sds_port
from app.use_cases.exceptions import SDSClaimEvidenceRetrievalError
from tests.e2e.auth import set_token_office_codes
from tests.e2e.factories import (
    create_application_in_db,
    create_claim_evidence_in_db,
    create_claim_for_reference,
)


def _create_claim_evidence(session, claim_id: int | None = None) -> ClaimEvidence:
    claim_evidence = ClaimEvidence(
        sds_file_name="stored-claim-evidence_abc123.pdf",
        file_name="claim_evidence.pdf",
        office_id="0U651L",
        claim_id=claim_id,
    )
    session.add(claim_evidence)
    session.commit()
    session.refresh(claim_evidence)
    return claim_evidence


class TestRetrieveClaimEvidence:
    def test_200_retrieve_claim_evidence_returns_file_content_before_claim_exists(
        self, session, client
    ):
        claim_evidence = _create_claim_evidence(session)

        response = client.get(
            f"/claims/{claim_evidence.claim_evidence_id}",
            headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
        )

        assert response.status_code == 200
        assert response.content == b"file bytes"

    def test_200_retrieve_claim_evidence_defaults_to_inline_disposition(
        self, session, client
    ):
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

    def test_200_retrieve_claim_evidence_supports_attachment_disposition(
        self, session, client
    ):
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
        self, session, client
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

    def test_200_retrieve_claim_evidence_returns_xlsx_content(self, session, client):
        claim_evidence = ClaimEvidence(
            sds_file_name="stored-claim-evidence_abc123.xlsx",
            file_name="claim_cost_template.xlsx",
            office_id="0U651L",
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

    def test_200_retrieve_claim_evidence_returns_xls_content(self, session, client):
        claim_evidence = ClaimEvidence(
            sds_file_name="stored-claim-evidence_abc123.xls",
            file_name="claim_cost_template.xls",
            office_id="0U651L",
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

    def test_404_retrieve_claim_evidence_returns_404_when_not_found(self, client):
        response = client.get(
            f"/claims/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
        )

        assert response.status_code == 404

    def test_415_retrieve_claim_evidence_returns_415_for_unsupported_mime_type(
        self, session, client
    ):
        claim_evidence = ClaimEvidence(
            sds_file_name="stored-claim-evidence_abc123.exe",
            file_name="claim_evidence.exe",
            office_id="0U651L",
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
        self, session, client, captured_sentry_events
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


class TestRetrieveClaimEvidenceOfficeIdCheck:
    @pytest.fixture
    def sds(self, client):
        sds = MagicMock()
        sds.retrieve_claim_evidence.side_effect = lambda key: iter([b"file bytes"])
        api.dependency_overrides[get_sds_port] = lambda: sds
        return sds

    @staticmethod
    def _create_file(session, file_type, office_id, firm_code):
        application = create_application_in_db(
            session,
            provider_overrides={"firm_code": firm_code, "office_id": office_id},
        )
        claim = create_claim_for_reference(
            session,
            application.laa_reference,
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
            file_name="evidence.pdf",
            claim_id=claim.claim_id if file_type != "cost_template" else None,
        )
        if file_type == "cost_template":
            session.add(
                ClaimCostTemplate(
                    claim_id=claim.claim_id,
                    claim_cost_template_file_id=evidence.claim_evidence_id,
                    claim_cost_template_file_name="evidence.pdf",
                )
            )
            session.commit()
        return evidence

    @pytest.mark.parametrize("disposition", ["inline", "attachment"])
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
    def test_200_provider_reads_file_when_its_office_id_is_in_the_token(
        self, session, client, sds, file_type, file_office, token_offices, disposition
    ):
        set_token_office_codes(token_offices)
        evidence = self._create_file(session, file_type, file_office, "0A123B")

        response = client.get(
            f"/claims/{evidence.claim_evidence_id}?disposition={disposition}",
            headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
        )

        assert response.status_code == 200
        assert response.content == b"file bytes"
        sds.retrieve_claim_evidence.assert_called_once_with("stored-file-key")

    @pytest.mark.parametrize("disposition", ["inline", "attachment"])
    @pytest.mark.parametrize(
        "file_type", ["poa_evidence", "final_bill_evidence", "cost_template"]
    )
    @pytest.mark.parametrize(
        ("firm_code", "file_office"),
        [("0A123B", "002"), ("ZZ999Z", "003")],
        ids=["same-firm-different-office", "different-firm"],
    )
    def test_404_provider_cannot_read_file_when_its_office_id_is_not_in_the_token(
        self, session, client, sds, file_type, firm_code, file_office, disposition
    ):
        set_token_office_codes({"0U651L"})
        evidence = self._create_file(session, file_type, file_office, firm_code)
        headers = {"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"}

        unknown_response = client.get(
            f"/claims/{uuid.uuid4()}?disposition={disposition}", headers=headers
        )
        response = client.get(
            f"/claims/{evidence.claim_evidence_id}?disposition={disposition}",
            headers=headers,
        )

        assert response.status_code == unknown_response.status_code == 404
        assert response.json() == unknown_response.json()
        sds.retrieve_claim_evidence.assert_not_called()

    @pytest.mark.parametrize(
        "caseworker_role",
        [Role.CLAIMS_CASEWORKER, Role.CUSTOMER_SERVICE_AGENT, Role.ASSURANCE],
    )
    @pytest.mark.parametrize(
        "file_type", ["poa_evidence", "final_bill_evidence", "cost_template"]
    )
    def test_200_caseworker_can_read_file_from_any_office(
        self, session, client, sds, caseworker_role, file_type
    ):
        evidence = self._create_file(session, file_type, "003", "ZZ999Z")

        response = client.get(
            f"/claims/{evidence.claim_evidence_id}",
            headers={"Authorization": f"Bearer {caseworker_role.value}"},
        )

        assert response.status_code == 200
        assert response.content == b"file bytes"
