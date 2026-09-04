from datetime import UTC, datetime

from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent


def _create_base_history_event(**overrides) -> HistoryEvent:
    defaults = {
        "event_reference": HistoryEventReference.APPLICATION_SUBMITTED,
        "timestamp": datetime(2026, 1, 1, tzinfo=UTC),
        "actor": "Provider",
        "actor_type": ActorType.PROVIDER,
        "application_id": 12345,
    }
    return HistoryEvent(**(defaults | overrides))


def test_history_event_laa_reference_returns_string_of_application_id():
    history_event = _create_base_history_event(application_id=12345)

    assert history_event.laa_reference == "12345"
