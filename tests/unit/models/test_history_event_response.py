from datetime import UTC, datetime

from app.models.history.enums import HistoryEventReference
from app.models.history.index import HistoryEventResponse


def test_model_dump_json_camel_cases_event_data_keys():
    response = HistoryEventResponse(
        timestamp=datetime.now(UTC),
        actor="Provider",
        event_reference=HistoryEventReference.CLAIM_SUBMITTED,
        event_data={
            "claim_type": "PAYMENT_ON_ACCOUNT",
            "related_link": "/certificate/123",
            "nested_data": {"submitted_by_user": "provider@example.com"},
        },
    )

    result = response.model_dump(mode="json", by_alias=True)

    assert result["eventData"] == {
        "claimType": "PAYMENT_ON_ACCOUNT",
        "relatedLink": "/certificate/123",
        "nestedData": {"submittedByUser": "provider@example.com"},
    }


def test_model_dump_json_leaves_event_data_as_none_when_not_present():
    response = HistoryEventResponse(
        timestamp=datetime.now(UTC),
        actor="Provider",
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        event_data=None,
    )

    result = response.model_dump(mode="json", by_alias=True)

    assert result["eventData"] is None
