from unittest.mock import MagicMock

import pytest

from app.contexts.user import set_entra_user_context
from app.models.history.enums import ActorType, HistoryEventReference
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.use_cases.create_note import CreateNoteUseCase
from app.use_cases.exceptions import ApplicationNotFoundError
from tests.unit.factories import create_base_application


def test_create_note_creates_caseworker_history_event_and_commits():
    application = create_base_application()
    application_lookup_port = MagicMock(spec=ApplicationLookupPort)
    application_lookup_port.get_application_by_laa_reference.return_value = application
    create_history_event_port = MagicMock(spec=CreateHistoryEventPort)
    use_case = CreateNoteUseCase(
        application_lookup_port=application_lookup_port,
        create_history_event_port=create_history_event_port,
    )
    set_entra_user_context(None, "Caseworker Name")

    use_case.execute(str(application.laa_reference), "Case note")

    application_lookup_port.get_application_by_laa_reference.assert_called_once_with(
        str(application.laa_reference)
    )
    create_history_event_port.create_history_event.assert_called_once_with(
        event_reference=HistoryEventReference.CASE_NOTE_ADDED,
        actor="Caseworker Name",
        actor_type=ActorType.CASEWORKER,
        laa_reference=application.laa_reference,
        event_data={"note_text": "Case note"},
    )
    create_history_event_port.commit.assert_called_once()
    create_history_event_port.rollback.assert_not_called()


def test_create_note_raises_when_application_is_not_found():
    application_lookup_port = MagicMock(spec=ApplicationLookupPort)
    application_lookup_port.get_application_by_laa_reference.return_value = None
    create_history_event_port = MagicMock(spec=CreateHistoryEventPort)
    use_case = CreateNoteUseCase(
        application_lookup_port=application_lookup_port,
        create_history_event_port=create_history_event_port,
    )

    with pytest.raises(
        ApplicationNotFoundError,
        match="Application 99999 not found",
    ):
        use_case.execute("99999", "Case note")

    application_lookup_port.get_application_by_laa_reference.assert_called_once_with(
        "99999"
    )
    create_history_event_port.create_history_event.assert_not_called()
    create_history_event_port.commit.assert_not_called()
    create_history_event_port.rollback.assert_not_called()


def test_create_note_rolls_back_when_history_event_creation_fails():
    application = create_base_application()
    application_lookup_port = MagicMock(spec=ApplicationLookupPort)
    application_lookup_port.get_application_by_laa_reference.return_value = application
    create_history_event_port = MagicMock(spec=CreateHistoryEventPort)
    create_history_event_port.create_history_event.side_effect = RuntimeError(
        "History event persistence failed"
    )
    use_case = CreateNoteUseCase(
        application_lookup_port=application_lookup_port,
        create_history_event_port=create_history_event_port,
    )

    with pytest.raises(
        RuntimeError,
        match="History event persistence failed",
    ):
        use_case.execute(str(application.laa_reference), "Case note")

    create_history_event_port.commit.assert_not_called()
    create_history_event_port.rollback.assert_called_once()


def test_create_note_rolls_back_when_commit_fails():
    application = create_base_application()
    application_lookup_port = MagicMock(spec=ApplicationLookupPort)
    application_lookup_port.get_application_by_laa_reference.return_value = application
    create_history_event_port = MagicMock(spec=CreateHistoryEventPort)
    create_history_event_port.commit.side_effect = RuntimeError("Commit failed")
    use_case = CreateNoteUseCase(
        application_lookup_port=application_lookup_port,
        create_history_event_port=create_history_event_port,
    )

    with pytest.raises(RuntimeError, match="Commit failed"):
        use_case.execute(str(application.laa_reference), "Case note")

    create_history_event_port.create_history_event.assert_called_once()
    create_history_event_port.commit.assert_called_once()
    create_history_event_port.rollback.assert_called_once()
