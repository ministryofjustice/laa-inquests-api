import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy.dialects import postgresql
from sqlmodel import Session, select

from app.adapters.claim_repository_adapter import ClaimRepositoryAdapter
from app.domain.payment_extract import PaymentExtractLine
from app.models.application.enums import PublicBodyId
from app.models.application.index import Application, ApplicationPublicBody
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimStatus,
    ClaimType,
    InquestOutcomeCode,
    InvoiceTypeCode,
    NumberOfCounselInstructed,
    POAType,
    ReasonCode,
    TaxCode,
)
from app.models.claim.index import (
    Claim,
    ClaimCostTemplate,
    ClaimDecision,
    ClaimDecisionAmount,
    ClaimEvidence,
    ClaimInquestOutcome,
    ClaimPaymentExtract,
    DecisionReason,
)
from tests.e2e.factories import create_claim_evidence_in_db, create_claim_in_db
from tests.unit.factories import (
    create_base_claim,
    create_base_claim_domain,
    create_base_final_bill_claim_domain,
)

OGD_WINDOW = (
    datetime(2025, 3, 1, tzinfo=UTC),
    datetime(2025, 4, 1, tzinfo=UTC),
)


@pytest.fixture
def adapter(session):
    return ClaimRepositoryAdapter(session)


@pytest.fixture
def application_id(session):
    return session.exec(select(Application)).first().application_id


@pytest.fixture
def claim(session, application_id):
    return create_claim_in_db(session, application_id=application_id)


def _paid_claim_with_extract(
    session,
    decided_at: datetime,
    *,
    claim_type: ClaimType = ClaimType.FINAL_BILL,
    invoice_type: InvoiceTypeCode = InvoiceTypeCode.FINAL_BILL_FEES,
    invoice_amount: str = "100.00",
    decision: ClaimDecisionStatus = ClaimDecisionStatus.PAY_IN_FULL,
) -> Claim:
    application_id = session.exec(select(Application)).first().application_id
    claim = create_claim_in_db(
        session, application_id=application_id, claim_type=claim_type
    )
    session.add(
        ClaimDecision(claim_id=claim.claim_id, decision=decision, created_at=decided_at)
    )
    session.add(
        ClaimPaymentExtract(
            claim_id=claim.claim_id,
            sequence_number=1,
            invoice_number=f"{claim.claim_reference}_001",
            invoice_amount=Decimal(invoice_amount),
            invoice_date=decided_at.date(),
            invoice_type=invoice_type,
            tax_code=TaxCode.GB_VAT_20,
        )
    )
    session.commit()
    return claim


class TestCreateClaim:
    def test_persists_claim_with_expected_values(
        self, session, adapter, application_id
    ):
        created = adapter.create_claim(
            application_id,
            create_base_claim_domain(
                poa_type=POAType.EXPERT_COST, vat_zero_total=Decimal("150.00")
            ),
            "claimant-123@provider.co.uk",
            Decimal("8000.00"),
        )
        stored = session.get(Claim, created.claim_id)

        assert created.claim_id is not None
        assert stored is not None
        assert stored.application_id == application_id
        assert stored.claim_type_id == ClaimType.PAYMENT_ON_ACCOUNT
        assert stored.total_profit_cost_net == Decimal("1000.00")
        assert stored.total_profit_cost_gross == Decimal("1200.00")
        assert stored.total_profit_cost_vat_zero == Decimal("150.00")
        assert stored.poa_type_id == POAType.EXPERT_COST
        assert stored.claimant_id == "claimant-123@provider.co.uk"
        assert stored.total_funds_remaining_after_claim == Decimal("8000.00")

    def test_defaults_status_to_submitted(self, adapter, application_id):
        created = adapter.create_claim(application_id, create_base_claim_domain(), None)

        assert created.status_id == ClaimStatus.SUBMITTED

    def test_sets_submission_date(self, adapter, application_id):
        created = adapter.create_claim(application_id, create_base_claim_domain(), None)

        assert created.submission_date is not None

    def test_persists_optional_fields_as_none_when_omitted(
        self, adapter, application_id
    ):
        created = adapter.create_claim(
            application_id, create_base_final_bill_claim_domain(), None
        )

        assert created.poa_type_id is None
        assert created.claimant_id is None

    def test_persists_final_bill_details(self, session, adapter, application_id):
        created = adapter.create_claim(
            application_id,
            create_base_final_bill_claim_domain(net=None, gross=None),
            None,
        )
        stored = session.get(Claim, created.claim_id)

        assert stored.has_counsel_been_paid is True
        assert stored.has_alternative_funding is False
        assert stored.has_recovery_costs_awarded is True
        assert stored.financial_recovery_previous_pre_certificate_costs == Decimal(
            "100.00"
        )
        assert stored.financial_recovery_cost == Decimal("200.00")
        assert stored.financial_recovery_damages == Decimal("300.00")
        assert stored.financial_recovery_interest == Decimal("50.00")
        assert stored.paying_party == "Test Council"
        assert stored.number_of_counsel_instructed == NumberOfCounselInstructed.TWO


class TestGetClaimsByApplicationId:
    def test_returns_all_claims_regardless_of_status(
        self, session, adapter, application_id
    ):
        statuses = {
            ClaimStatus.ACCEPTED,
            ClaimStatus.REJECTED,
            ClaimStatus.REJECTED_WITH_AMENDMENT,
        }
        for status in statuses:
            create_claim_in_db(session, application_id=application_id, status=status)

        result = adapter.get_claims_by_application_id(application_id)

        assert {c.status_id for c in result} == statuses

    def test_returns_claims_for_application(self, session, adapter, application_id):
        create_claim_in_db(session, application_id=application_id)
        create_claim_in_db(session, application_id=application_id)

        results = adapter.get_claims_by_application_id(application_id)

        assert len(results) == 2
        assert all(c.application_id == application_id for c in results)

    def test_returns_empty_list_when_no_claims(self, adapter, application_id):
        assert adapter.get_claims_by_application_id(application_id) == []


class TestLinkInquestOutcomesToClaim:
    def test_persists_link_rows(self, session, adapter, claim):
        adapter.link_inquest_outcomes_to_claim(
            claim.claim_id,
            [
                InquestOutcomeCode.NARRATIVE_CONCLUSION,
                InquestOutcomeCode.NATURAL_CAUSES,
            ],
        )
        adapter.commit()

        stored = session.exec(
            select(ClaimInquestOutcome).where(
                ClaimInquestOutcome.claim_id == claim.claim_id
            )
        ).all()
        assert {row.inquest_outcome_id for row in stored} == {
            InquestOutcomeCode.NARRATIVE_CONCLUSION,
            InquestOutcomeCode.NATURAL_CAUSES,
        }


class TestLinkCostTemplateToClaim:
    def test_persists_row(self, session, adapter, claim):
        file_id = uuid.uuid4()

        adapter.link_cost_template_to_claim(
            claim.claim_id, file_id, "final_bill_costs.xlsx"
        )
        adapter.commit()

        stored = session.exec(
            select(ClaimCostTemplate).where(
                ClaimCostTemplate.claim_id == claim.claim_id
            )
        ).all()
        assert len(stored) == 1
        assert stored[0].claim_cost_template_file_id == file_id
        assert stored[0].claim_cost_template_file_name == "final_bill_costs.xlsx"


class TestGetClaimByReference:
    def test_for_assessment_locks_and_refreshes_claim(self):
        session = MagicMock(spec=Session)
        claim = create_base_claim(claim_id=1, claim_reference="INQC-0000-0001")
        session.exec.return_value.first.return_value = claim
        adapter = ClaimRepositoryAdapter(session)

        result = adapter.get_claim_by_reference(
            claim.claim_reference, for_assessment=True
        )

        assert result is claim
        session.exec.assert_called_once()
        statement = session.exec.call_args.args[0]
        compiled = statement.compile(dialect=postgresql.dialect())
        assert "WHERE claim.claim_reference =" in str(compiled)
        assert str(compiled).endswith(" FOR UPDATE")
        assert compiled.params == {"claim_reference_1": claim.claim_reference}
        assert statement.get_execution_options()["populate_existing"] is True
        session.commit.assert_not_called()
        session.rollback.assert_not_called()


class TestGetPaymentExtractsByClaimId:
    def test_returns_lines_in_sequence_order(self, adapter, claim):
        adapter.create_payment_extract(
            claim_id=claim.claim_id,
            lines=[
                PaymentExtractLine(
                    sequence_number=2,
                    invoice_number=f"{claim.claim_id}_002",
                    invoice_amount=Decimal("200.00"),
                    invoice_date=datetime.now(UTC).date(),
                    invoice_type=InvoiceTypeCode.POA,
                    tax_code=TaxCode.ZERO_VAT,
                ),
                PaymentExtractLine(
                    sequence_number=1,
                    invoice_number=f"{claim.claim_id}_001",
                    invoice_amount=Decimal("800.00"),
                    invoice_date=datetime.now(UTC).date(),
                    invoice_type=InvoiceTypeCode.POA,
                    tax_code=TaxCode.GB_VAT_20,
                ),
            ],
        )
        adapter.commit()

        results = adapter.get_payment_extracts_by_claim_id(claim.claim_id)

        assert [line.sequence_number for line in results] == [1, 2]
        assert results[0].invoice_number == f"{claim.claim_id}_001"
        assert results[1].invoice_number == f"{claim.claim_id}_002"

    def test_returns_empty_list_when_none(self, adapter, claim):
        assert adapter.get_payment_extracts_by_claim_id(claim.claim_id) == []


class TestGetOpenClaims:
    def test_returns_only_open_claims(self, session, adapter, application_id):
        open_claim = create_claim_in_db(session, application_id=application_id)
        create_claim_in_db(
            session, application_id=application_id, status=ClaimStatus.REJECTED
        )

        results = adapter.get_open_claims()

        assert [c.claim_id for c in results] == [open_claim.claim_id]

    def test_returned_claims_have_matching_application(self, adapter, claim):
        results = adapter.get_open_claims()

        for open_claim in results:
            assert open_claim.application_id == open_claim.application.application_id

    def test_orders_by_submission_date_ascending(
        self, session, adapter, application_id
    ):
        newer_claim = create_claim_in_db(
            session,
            application_id=application_id,
            submission_date=datetime(2026, 6, 1, tzinfo=UTC),
        )
        older_claim = create_claim_in_db(
            session,
            application_id=application_id,
            submission_date=datetime(2026, 1, 1, tzinfo=UTC),
        )

        results = adapter.get_open_claims()

        assert [c.claim_id for c in results] == [
            older_claim.claim_id,
            newer_claim.claim_id,
        ]


class TestCreateClaimDecision:
    def test_persists_decision_with_expected_values(self, session, adapter, claim):
        decision = adapter.create_claim_decision(
            claim.claim_id, ClaimDecisionStatus.REJECT
        )
        stored = session.get(ClaimDecision, decision.claim_decision_id)

        assert decision.claim_decision_id is not None
        assert stored is not None
        assert stored.claim_id == claim.claim_id
        assert stored.decision == ClaimDecisionStatus.REJECT
        assert stored.created_at is not None


class TestCreateDecisionReason:
    def test_persists_reason_with_expected_values(self, session, adapter, claim):
        decision = adapter.create_claim_decision(
            claim.claim_id, ClaimDecisionStatus.REJECT
        )

        reason = adapter.create_decision_reason(
            decision.claim_decision_id,
            ReasonCode.MAX_POA_CLAIMS_EXCEEDED,
        )
        stored = session.get(DecisionReason, reason.decision_reason_id)

        assert reason.decision_reason_id is not None
        assert stored is not None
        assert stored.claim_decision_id == decision.claim_decision_id
        assert stored.reason_code == ReasonCode.MAX_POA_CLAIMS_EXCEEDED
        assert stored.justification is None

    def test_persists_justification_when_provided(self, adapter, claim):
        decision = adapter.create_claim_decision(
            claim.claim_id, ClaimDecisionStatus.REJECT
        )

        reason = adapter.create_decision_reason(
            decision.claim_decision_id,
            ReasonCode.MAX_POA_CLAIMS_EXCEEDED,
            justification="Some justification text",
        )

        assert reason.justification == "Some justification text"


class TestCreateClaimDecisionAmount:
    def test_persists_amounts_with_expected_values(self, session, adapter, claim):
        decision = adapter.create_claim_decision(
            claim.claim_id, ClaimDecisionStatus.PAY_IN_FULL
        )

        amount = adapter.create_claim_decision_amount(
            decision.claim_decision_id,
            profit_cost_net=Decimal("1000.00"),
            profit_cost_gross=Decimal("1200.00"),
            profit_cost_vat_zero=Decimal("500.00"),
            disbursement_net=Decimal("100.00"),
            disbursement_gross=Decimal("120.00"),
            disbursement_vat_zero=Decimal("50.00"),
        )
        stored = session.get(ClaimDecisionAmount, amount.claim_decision_amount_id)

        assert amount.claim_decision_amount_id is not None
        assert stored is not None
        assert stored.claim_decision_id == decision.claim_decision_id
        assert stored.profit_cost_net == Decimal("1000.00")
        assert stored.profit_cost_gross == Decimal("1200.00")
        assert stored.profit_cost_vat_zero == Decimal("500.00")
        assert stored.disbursement_net == Decimal("100.00")
        assert stored.disbursement_gross == Decimal("120.00")
        assert stored.disbursement_vat_zero == Decimal("50.00")

    def test_persists_none_when_fields_omitted(self, adapter, claim):
        decision = adapter.create_claim_decision(
            claim.claim_id, ClaimDecisionStatus.PAY_IN_FULL
        )

        amount = adapter.create_claim_decision_amount(decision.claim_decision_id)

        assert amount.profit_cost_net is None
        assert amount.profit_cost_gross is None
        assert amount.profit_cost_vat_zero is None
        assert amount.disbursement_net is None
        assert amount.disbursement_gross is None
        assert amount.disbursement_vat_zero is None


class TestGetClaimDecisionAmountByDecisionId:
    def test_returns_the_amount_for_the_decision(self, adapter, claim):
        decision = adapter.create_claim_decision(
            claim.claim_id, ClaimDecisionStatus.PAY_IN_FULL
        )
        adapter.create_claim_decision_amount(
            decision.claim_decision_id,
            profit_cost_net=Decimal("1000.00"),
            profit_cost_gross=Decimal("1200.00"),
            disbursement_net=Decimal("100.00"),
            disbursement_gross=Decimal("120.00"),
        )

        amount = adapter.get_claim_decision_amount_by_decision_id(
            decision.claim_decision_id
        )

        assert amount is not None
        assert amount.claim_decision_id == decision.claim_decision_id
        assert amount.profit_cost_net == Decimal("1000.00")
        assert amount.disbursement_gross == Decimal("120.00")

    def test_returns_none_when_decision_has_no_amount(self, adapter, claim):
        decision = adapter.create_claim_decision(
            claim.claim_id, ClaimDecisionStatus.REJECT
        )

        amount = adapter.get_claim_decision_amount_by_decision_id(
            decision.claim_decision_id
        )

        assert amount is None


class TestLinkEvidenceToClaim:
    def test_sets_claim_id_on_existing_evidence(self, session, adapter, claim):
        evidence = create_claim_evidence_in_db(session)

        adapter.link_evidence_to_claim(claim.claim_id, [evidence.claim_evidence_id])

        stored = session.get(ClaimEvidence, evidence.claim_evidence_id)
        assert stored.claim_id == claim.claim_id

    def test_ignores_unknown_evidence_ids(self, adapter, claim):
        adapter.link_evidence_to_claim(
            claim.claim_id, [uuid.uuid4()]
        )  # should not raise


class TestDeleteClaimEvidenceById:
    def test_deletes_existing_evidence(self, session, adapter):
        evidence = create_claim_evidence_in_db(session)

        deleted = adapter.delete_claim_evidence_by_id(evidence.claim_evidence_id)

        assert deleted is True
        assert session.get(ClaimEvidence, evidence.claim_evidence_id) is None

    def test_returns_false_for_unknown_id(self, adapter):
        assert adapter.delete_claim_evidence_by_id(uuid.uuid4()) is False


class TestUpdateClaimStatus:
    def test_sets_status_on_claim(self, session, adapter, claim):
        adapter.update_claim_status(claim.claim_id, ClaimStatus.REJECTED)
        session.refresh(claim)

        assert claim.status_id == ClaimStatus.REJECTED


class TestCommitAndRollback:
    def test_commit_commits_session(self, session, adapter, application_id):
        adapter.create_claim(application_id, create_base_claim_domain(), None)

        adapter.commit()

        assert len(session.exec(select(Claim)).all()) == 1

    def test_rollback_rolls_back_unflushed_changes(
        self, session, adapter, application_id
    ):
        adapter.create_claim(application_id, create_base_claim_domain(), None)

        adapter.rollback()

        assert session.exec(select(Claim)).all() == []


class TestGenerateClaimReference:
    def test_has_expected_format(self, adapter):
        for _ in range(10):
            reference = adapter._generate_claim_reference()
            prefix, first, second = reference.split("-")
            assert prefix == "INQC"
            assert len(first) == 4
            assert len(second) == 4

    def test_returns_unique_references(self, adapter):
        assert (
            adapter._generate_claim_reference() != adapter._generate_claim_reference()
        )

    def test_excludes_ambiguous_characters(self, adapter):
        for _ in range(10):
            reference = adapter._generate_claim_reference()
            # Ignore the "INQC-" prefix and check the random segments only.
            assert all(char not in reference[5:] for char in "B8G6I10OQDS5Z2")


class TestGetClaimReference:
    def test_retries_when_banned_word_generated(self, adapter):
        adapter._generate_claim_reference = MagicMock(
            side_effect=["INQC-XXXY-YYYY", "INQC-YYYY-YYYY"]
        )
        adapter.reference_rules.contains_banned_word = MagicMock(
            side_effect=[True, False]
        )

        reference = adapter._get_claim_reference()

        assert reference == "INQC-YYYY-YYYY"
        assert adapter._generate_claim_reference.call_count == 2

    def test_retries_when_reference_already_exists(self, adapter, claim):
        adapter._generate_claim_reference = MagicMock(
            side_effect=[claim.claim_reference, "INQC-YYYY-YYYY"]
        )

        reference = adapter._get_claim_reference()

        assert reference == "INQC-YYYY-YYYY"
        assert adapter._generate_claim_reference.call_count == 2

    def test_raises_after_max_attempts(self, adapter):
        adapter._generate_claim_reference = MagicMock(return_value="INQC-XXXX-XXXX")
        adapter.reference_rules.contains_banned_word = MagicMock(return_value=True)

        with pytest.raises(
            RuntimeError,
            match="Maximum attempts reached for generating claim reference",
        ):
            adapter._get_claim_reference()


class TestGetOgdPublicBodiesByApplication:
    def test_returns_bodies_as_enum_members(self, session, adapter, application_id):
        session.add(
            ApplicationPublicBody(
                application_id=application_id,
                public_body_id=PublicBodyId.MINISTRY_OF_JUSTICE,
            )
        )
        session.commit()
        _paid_claim_with_extract(session, datetime(2025, 3, 15, tzinfo=UTC))

        result = adapter.get_ogd_public_bodies_by_application(*OGD_WINDOW)

        assert set(result) == {application_id}
        assert set(result[application_id]) == {
            PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
            PublicBodyId.MINISTRY_OF_JUSTICE,
        }


class TestIterOgdCostsReportLines:
    def test_filters_on_decision_date_window_only(self, session, adapter):
        inside = _paid_claim_with_extract(session, datetime(2025, 3, 1, tzinfo=UTC))
        _paid_claim_with_extract(session, datetime(2025, 2, 28, 23, 59, 59, tzinfo=UTC))
        _paid_claim_with_extract(session, datetime(2025, 4, 1, tzinfo=UTC))
        _paid_claim_with_extract(
            session,
            datetime(2025, 3, 10, tzinfo=UTC),
            decision=ClaimDecisionStatus.REJECT,
        )

        lines = list(adapter.iter_ogd_costs_report_lines(*OGD_WINDOW))

        assert [line.invoice_number for line in lines] == [
            f"{inside.claim_reference}_001"
        ]

    def test_maps_line_fields(self, session, adapter):
        claim = _paid_claim_with_extract(
            session,
            datetime(2025, 3, 15, 12, tzinfo=UTC),
            claim_type=ClaimType.NIL_BILL,
            invoice_amount="0.00",
        )

        [line] = adapter.iter_ogd_costs_report_lines(*OGD_WINDOW)

        assert line.application_id == claim.application_id
        assert line.claim_decision == ClaimDecisionStatus.PAY_IN_FULL
        assert line.claim_type == ClaimType.NIL_BILL
        assert line.invoice_type == InvoiceTypeCode.FINAL_BILL_FEES
        assert line.invoice_amount == Decimal("0.00")
        assert line.tax_code == TaxCode.GB_VAT_20
        assert line.laa_reference == "INQ-123-456"
        assert (line.deceased_first_name, line.deceased_last_name) == (
            "Test",
            "Surname",
        )
        assert line.deceased_date_of_death == "2026-01-01"

    def test_returns_recoupment_with_final_bill_decision(self, session, adapter):
        final_bill = _paid_claim_with_extract(
            session,
            datetime(2025, 3, 20, tzinfo=UTC),
            invoice_type=InvoiceTypeCode.RECOUPED,
            invoice_amount="-100.00",
        )

        [line] = adapter.iter_ogd_costs_report_lines(*OGD_WINDOW)

        assert line.invoice_type == InvoiceTypeCode.RECOUPED
        assert line.invoice_amount == Decimal("-100.00")
        assert line.claim_type == final_bill.claim_type_id
        assert line.claim_decision_date.date().isoformat() == "2025-03-20"
