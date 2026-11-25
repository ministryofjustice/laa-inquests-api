from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlmodel import select

from app import api
from app.auth.rbac import Role
from app.models.application.enums import MeritsDecision
from app.models.application.index import Application
from app.models.claim.enums import ClaimStatus, ClaimType, InvoiceTypeCode, TaxCode
from app.models.claim.index import ClaimPaymentExtract
from app.routers.applications import get_provider_details_port
from tests.e2e.factories import create_claim_in_db
from tests.helpers.csv_helpers import parse_csv_rows

FORMULA_TRIGGERS = [
    "=cmd|' /C calc'!A0",
    "+1",
    "-1",
    "@SUM(A1)",
    " =cmd",
    "\t=cmd",
    "＝cmd",
]


def _provider_details_with_firm_name(firm_name: str) -> None:
    mock_port = MagicMock()
    mock_port.get_firms_by_ids.side_effect = lambda firm_ids: [
        {"firmNumber": firm_id, "firmName": firm_name} for firm_id in firm_ids
    ]
    api.dependency_overrides[get_provider_details_port] = lambda: mock_port


@pytest.mark.parametrize("firm_name", FORMULA_TRIGGERS)
class TestFirmNameIsNeutralisedInEveryReportThatExportsIt:
    def test_applications_backlog(self, session, client, firm_name):
        application = session.exec(select(Application)).first()
        application.proceeding.merits_decision = MeritsDecision.SUBMITTED
        session.add(application.proceeding)
        session.commit()
        _provider_details_with_firm_name(firm_name)

        response = client.get(
            "/reports/applications/backlog",
            headers={
                "Authorization": f"Bearer {Role.APPLICATION_WORKFLOW_REPORTING.value}"
            },
        )

        assert response.status_code == 200
        assert parse_csv_rows(response.text)[0]["Firm name"] == f"'{firm_name}"

    def test_claims_backlog(self, session, client, firm_name):
        application = session.exec(select(Application)).first()
        create_claim_in_db(
            session,
            application_id=application.application_id,
            status=ClaimStatus.SUBMITTED,
            submission_date=datetime(2026, 1, 1, tzinfo=UTC),
            total_profit_cost_vat_zero=Decimal("0.00"),
        )
        _provider_details_with_firm_name(firm_name)

        response = client.get(
            "/reports/claims/backlog",
            headers={"Authorization": f"Bearer {Role.CLAIM_WORKFLOW_REPORTING.value}"},
        )

        assert response.status_code == 200
        row = parse_csv_rows(response.text)[0]
        assert row["Firm Name"] == f"'{firm_name}"
        assert row["Total 0% VAT claim value"] == "0.00"

    def test_payment_extract_vendor_name(self, session, client, firm_name):
        application = session.exec(select(Application)).first()
        claim = create_claim_in_db(
            session,
            application_id=application.application_id,
            claim_type=ClaimType.FINAL_BILL,
        )
        session.add(
            ClaimPaymentExtract(
                claim_id=claim.claim_id,
                sequence_number=1,
                invoice_number=f"{claim.claim_reference}_001",
                invoice_amount=Decimal("-100.00"),
                invoice_date=datetime(2025, 3, 10, tzinfo=UTC).date(),
                invoice_type=InvoiceTypeCode.FINAL_BILL_FEES,
                tax_code=TaxCode.GB_VAT_20,
                created_at=datetime(2025, 3, 15, 12, 0, tzinfo=UTC),
            )
        )
        session.commit()
        _provider_details_with_firm_name(firm_name)

        response = client.get(
            "/reports/payment-extract",
            params={"from": "2025-03-01", "to": "2025-03-30"},
            headers={"Authorization": f"Bearer {Role.FINANCE.value}"},
        )

        assert response.status_code == 200
        row = parse_csv_rows(response.text)[0]
        assert row["Vendor Name"] == f"'{firm_name}"
        assert row["Invoice Amount"] == "-100.00"
