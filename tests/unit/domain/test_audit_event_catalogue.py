import pytest

from app.domain.audit_event_catalogue import (
    InvalidEventDataError,
    UnknownEventReferenceError,
    describe_event,
)


@pytest.mark.parametrize(
    ("event_reference", "title", "description"),
    [
        ("EVT-BUS-APP-001", "Application submitted", "Application received"),
        ("EVT-BUS-APP-003", "Certificate created", "Certificate created"),
        (
            "EVT-COM-APP-001",
            "Application submission confirmation",
            "Application submission confirmation sent",
        ),
        (
            "EVT-COM-APP-002",
            "Application granted (Email)",
            "Application granted email sent",
        ),
        (
            "EVT-COM-APP-003",
            "Application granted (Letter)",
            "Application granted letter sent",
        ),
        ("EVT-COM-APP-004", "Application refused", "Application refused email sent"),
        (
            "EVT-COM-CLM-001",
            "Claim submission confirmation",
            "Claim submission confirmation sent",
        ),
        ("EVT-COM-CLM-002", "Claim approved", "Claim approved email sent"),
        ("EVT-COM-CLM-003", "Claim Rejected", "Claim rejected email sent"),
    ],
)
def test_describes_static_history_events(event_reference, title, description):
    described = describe_event(event_reference, None)

    assert described.title == title
    assert described.description == description


CLAIM_REFERENCE = "INQC-AAAA-BBBB"


@pytest.mark.parametrize(
    ("event_reference", "event_data", "title", "description"),
    [
        (
            "EVT-BUS-X-001",
            {"note_text": "Called the provider"},
            "Case note added",
            "Caseworker note added\nCalled the provider",
        ),
        (
            "EVT-BUS-APP-002",
            {"merits_decision": "Granted"},
            "Application assessment complete",
            "Application granted",
        ),
        (
            "EVT-BUS-APP-002",
            {
                "merits_decision": "Refused",
                "refusal_reason": "NOT_IN_SCOPE",
                "refusal_justification": "Outside the scope of the scheme",
            },
            "Application assessment complete",
            "Application refused\nNot in scope\nOutside the scope of the scheme",
        ),
        (
            "EVT-BUS-APP-004",
            {
                "old_public_bodies": ["DEPARTMENT_FOR_TRANSPORT"],
                "new_public_bodies": ["HOME_OFFICE", "CABINET_OFFICE"],
            },
            "Interested party updated",
            "Interested parties updated from DEPARTMENT_FOR_TRANSPORT to HOME_OFFICE, CABINET_OFFICE",
        ),
        (
            "EVT-BUS-CLM-001",
            {"claim_type": "FINAL_BILL", "claim_reference": CLAIM_REFERENCE},
            "Claim submitted",
            f"Final bill claim received: {CLAIM_REFERENCE}",
        ),
        (
            "EVT-BUS-CLM-002",
            {
                "claim_type": "PAYMENT_ON_ACCOUNT",
                "claim_reference": CLAIM_REFERENCE,
                "claim_decision": "PAY_IN_FULL",
            },
            "Claim assessment complete",
            f"Payment on account claim pay in full: {CLAIM_REFERENCE}",
        ),
        (
            "EVT-BUS-CLM-002",
            {
                "claim_type": "FINAL_BILL",
                "claim_reference": CLAIM_REFERENCE,
                "claim_decision": "REJECTED",
                "decision_justification": "Evidence is missing",
            },
            "Claim assessment complete",
            "Final bill claim rejected\nEvidence is missing",
        ),
        (
            "EVT-BUS-CLM-002",
            {
                "claim_type": "FINAL_BILL",
                "claim_reference": CLAIM_REFERENCE,
                "claim_decision": "REJECTED",
                "decision_justification": "   ",
            },
            "Claim assessment complete",
            f"Final bill claim rejected: {CLAIM_REFERENCE}",
        ),
        (
            "EVT-BUS-CLM-003",
            {"claim_reference": CLAIM_REFERENCE},
            "POA auto-approved",
            f"POA claim {CLAIM_REFERENCE} auto-approved",
        ),
        (
            "EVT-BUS-CLM-004",
            {"claim_reference": CLAIM_REFERENCE},
            "POA auto-rejected",
            f"POA claim {CLAIM_REFERENCE} auto-rejected",
        ),
    ],
)
def test_describes_dynamic_history_events_from_event_data(
    event_reference, event_data, title, description
):
    described = describe_event(event_reference, event_data)

    assert described.title == title
    assert described.description == description


@pytest.mark.parametrize(
    ("event_reference", "event_data", "title", "description"),
    [
        ("EVT-AUD-001", None, "Application viewed", "Application viewed"),
        ("EVT-AUD-003", None, "Certificate viewed", "Certificate viewed"),
        (
            "EVT-AUD-002",
            {"report_name": "Payment Extract"},
            "Report downloaded",
            "Payment Extract downloaded",
        ),
    ],
)
def test_describes_audit_events(event_reference, event_data, title, description):
    described = describe_event(event_reference, event_data)

    assert described.title == title
    assert described.description == description


def test_unknown_event_reference_raises_an_error():
    with pytest.raises(UnknownEventReferenceError, match="EVT-BUS-ZZZ-999"):
        describe_event("EVT-BUS-ZZZ-999", None)


@pytest.mark.parametrize(
    ("event_reference", "event_data"),
    [
        ("EVT-BUS-X-001", None),
        ("EVT-BUS-APP-002", {}),
        ("EVT-BUS-APP-002", {"merits_decision": "Refused"}),
        ("EVT-BUS-APP-004", {"old_public_bodies": []}),
        ("EVT-BUS-CLM-001", {"claim_type": "FINAL_BILL"}),
        ("EVT-BUS-CLM-003", {}),
        ("EVT-AUD-002", None),
    ],
)
def test_missing_event_data_raises_an_error(event_reference, event_data):
    with pytest.raises(InvalidEventDataError, match=event_reference):
        describe_event(event_reference, event_data)
