from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.domain.decisions_report import (
    DecisionsReportSourceRecord,
    InvalidDecisionRecordError,
    build_decisions_report_row,
    neutralise_csv_formula,
)
from app.models.history.enums import ActorType, HistoryEventReference

DECIDED_AT = datetime(2025, 3, 15, 13, 5, 9, tzinfo=UTC)
APPLICATION_SUBMITTED_AT = datetime(2025, 3, 2, 9, 30, tzinfo=UTC)
CLAIM_SUBMITTED_AT = datetime(2025, 3, 4, 8, 0, tzinfo=UTC)
_SYSTEM_ACTOR = {
    "actor": "System",
    "actor_type": ActorType.SYSTEM,
    "actor_email_address": None,
}


def _record(**overrides) -> DecisionsReportSourceRecord:
    defaults = {
        "event_reference": HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
        "decided_at": DECIDED_AT,
        "actor": "Jane Smith",
        "actor_type": ActorType.CASEWORKER,
        "actor_email_address": "jane.smith@example.com",
        "event_data": {"merits_decision": "Granted"},
        "laa_reference": "INQ-X7K-4P9",
        "application_submitted_at": APPLICATION_SUBMITTED_AT,
        "claim_submitted_at": None,
    }
    return DecisionsReportSourceRecord(**(defaults | overrides))


def _claim_record(event_reference, event_data, **overrides):
    return _record(
        event_reference=event_reference,
        event_data={"claim_reference": "INQC-7X4K-B2M5"} | event_data,
        claim_submitted_at=CLAIM_SUBMITTED_AT,
        **overrides,
    )


class TestApplicationDecisions:
    def test_refused_maps_reason_label_and_justification(self):
        row = build_decisions_report_row(
            _record(
                event_data={
                    "merits_decision": "Refused",
                    "refusal_reason": "NOT_IN_SCOPE",
                    "refusal_justification": "Out of scope",
                }
            )
        )

        assert row.as_list() == [
            "Application",
            "INQ-X7K-4P9",
            "",
            "Refused",
            "02-03-2025",
            "15-03-2025",
            "13:05:09",
            "jane.smith@example.com",
            "Not in scope",
            "Out of scope",
        ]

    @pytest.mark.parametrize(
        "reason,label",
        [
            ("NOT_IN_SCOPE", "Not in scope"),
            ("INSUFFICIENT_INFORMATION", "Insufficient information"),
            ("DUPLICATE_CASE", "Duplicate case"),
        ],
    )
    def test_refusal_reason_labels(self, reason, label):
        row = build_decisions_report_row(
            _record(
                event_data={
                    "merits_decision": "Refused",
                    "refusal_reason": reason,
                    "refusal_justification": "text",
                }
            )
        )

        assert row.refusal_reason == label

    def test_granted_has_blank_refusal_reason_and_justification(self):
        row = build_decisions_report_row(_record())

        assert row.submission_type == "Application"
        assert row.decision == "Granted"
        assert row.claim_reference == ""
        assert row.refusal_reason == ""
        assert row.justification == ""

    def test_unknown_merits_decision_is_rejected(self):
        with pytest.raises(InvalidDecisionRecordError):
            build_decisions_report_row(_record(event_data={"merits_decision": "?"}))

    def test_missing_event_data_is_rejected(self):
        with pytest.raises(InvalidDecisionRecordError):
            build_decisions_report_row(_record(event_data=None))

    @pytest.mark.parametrize("reason", [None, "MADE_UP"])
    def test_refused_with_missing_or_unknown_reason_is_rejected(self, reason):
        with pytest.raises(InvalidDecisionRecordError):
            build_decisions_report_row(
                _record(
                    event_data={
                        "merits_decision": "Refused",
                        "refusal_reason": reason,
                        "refusal_justification": "text",
                    }
                )
            )


class TestClaimDecisions:
    def test_pay_in_full_row(self):
        row = build_decisions_report_row(
            _claim_record(
                HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
                {"claim_decision": "PAY_IN_FULL"},
            )
        )

        assert row.as_list() == [
            "Claim",
            "INQ-X7K-4P9",
            "INQC-7X4K-B2M5",
            "Pay in full",
            "04-03-2025",
            "15-03-2025",
            "13:05:09",
            "jane.smith@example.com",
            "",
            "",
        ]

    def test_manual_rejection_includes_justification(self):
        row = build_decisions_report_row(
            _claim_record(
                HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
                {"claim_decision": "REJECTED", "decision_justification": "Too high"},
            )
        )

        assert row.decision == "Rejected"
        assert row.justification == "Too high"
        assert row.refusal_reason == ""

    def test_poa_auto_approved_is_pay_in_full(self):
        row = build_decisions_report_row(
            _claim_record(HistoryEventReference.POA_AUTO_APPROVED, {}, **_SYSTEM_ACTOR)
        )

        assert row.decision == "Pay in full"
        assert row.who == "System"
        assert row.justification == ""

    def test_poa_auto_rejected_is_rejected(self):
        row = build_decisions_report_row(
            _claim_record(HistoryEventReference.POA_AUTO_REJECTED, {}, **_SYSTEM_ACTOR)
        )

        assert row.decision == "Rejected"
        assert row.who == "System"
        assert row.justification == ""

    def test_unknown_claim_decision_is_rejected(self):
        with pytest.raises(InvalidDecisionRecordError):
            build_decisions_report_row(
                _claim_record(
                    HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
                    {"claim_decision": "SOMETHING_ELSE"},
                )
            )

    def test_missing_claim_reference_is_rejected(self):
        with pytest.raises(InvalidDecisionRecordError):
            build_decisions_report_row(
                _record(
                    event_reference=HistoryEventReference.POA_AUTO_APPROVED,
                    event_data={},
                    claim_submitted_at=CLAIM_SUBMITTED_AT,
                )
            )

    def test_missing_claim_submission_date_is_rejected(self):
        with pytest.raises(InvalidDecisionRecordError):
            build_decisions_report_row(
                _record(
                    event_reference=HistoryEventReference.POA_AUTO_APPROVED,
                    event_data={"claim_reference": "INQC-7X4K-B2M5"},
                    claim_submitted_at=None,
                )
            )


class TestUtcFormatting:
    def test_naive_datetimes_are_treated_as_utc(self):
        row = build_decisions_report_row(
            _record(
                decided_at=datetime(2025, 3, 15, 23, 59, 59, tzinfo=UTC).replace(
                    tzinfo=None
                ),
                application_submitted_at=datetime(2025, 3, 2, tzinfo=UTC).replace(
                    tzinfo=None
                ),
            )
        )

        assert row.date_of_decision == "15-03-2025"
        assert row.time_of_decision == "23:59:59"
        assert row.submission_date == "02-03-2025"

    def test_aware_datetimes_are_converted_to_utc(self):
        plus_two = timezone(timedelta(hours=2))

        row = build_decisions_report_row(
            _record(decided_at=datetime(2025, 3, 16, 0, 30, tzinfo=plus_two))
        )

        assert row.date_of_decision == "15-03-2025"
        assert row.time_of_decision == "22:30:00"


class TestNeutraliseCsvFormula:
    @pytest.mark.parametrize("value", ["=SUM(A1)", "+1", "-1", "@cmd", "\tx", "\rx"])
    def test_prefixes_single_quote_to_formula_triggers(self, value):
        assert neutralise_csv_formula(value) == f"'{value}"

    @pytest.mark.parametrize("value", ["", "Plain text", "a=b", "Jane Smith"])
    def test_leaves_other_text_unchanged(self, value):
        assert neutralise_csv_formula(value) == value

    def test_justification_and_who_are_neutralised_in_row(self):
        row = build_decisions_report_row(
            _record(
                actor_email_address="=cmd@example.com",
                event_data={
                    "merits_decision": "Refused",
                    "refusal_reason": "NOT_IN_SCOPE",
                    "refusal_justification": "@SUM(1)",
                },
            )
        )

        assert row.who == "'=cmd@example.com"
        assert row.justification == "'@SUM(1)"


class TestWho:
    def test_caseworker_who_is_the_email_address(self):
        row = build_decisions_report_row(_record())

        assert row.who == "jane.smith@example.com"

    @pytest.mark.parametrize("missing_email", [None, ""])
    def test_caseworker_without_stored_email_falls_back_to_actor_name(
        self, missing_email
    ):
        row = build_decisions_report_row(_record(actor_email_address=missing_email))

        assert row.who == "Jane Smith"

    def test_actor_name_is_not_used_when_an_email_is_stored(self):
        row = build_decisions_report_row(_record())

        assert "Jane Smith" not in row.as_list()

    def test_actor_name_fallback_is_csv_formula_neutralised(self):
        row = build_decisions_report_row(
            _record(actor="=Jane", actor_email_address=None)
        )

        assert row.who == "'=Jane"

    @pytest.mark.parametrize(
        "reference",
        [
            HistoryEventReference.POA_AUTO_APPROVED,
            HistoryEventReference.POA_AUTO_REJECTED,
        ],
    )
    def test_system_actor_who_is_system_even_if_an_email_is_present(self, reference):
        row = build_decisions_report_row(
            _claim_record(
                reference,
                {},
                actor="System",
                actor_type=ActorType.SYSTEM,
                actor_email_address="ignored@example.com",
            )
        )

        assert row.who == "System"
