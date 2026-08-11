import uuid
from unittest.mock import MagicMock

import pytest

from app.models.application.index import ApplicationCreate
from app.models.history.enums import ActorType, HistoryEventReference
from app.ports.create_application_port import CreateApplicationPort
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.ports.gov_notify_port import GovNotifyPort
from app.use_cases.create_application import CreateApplicationUseCase
from tests.unit.factories import create_base_application


def _make_request(email_address: str = "provider@example.com") -> ApplicationCreate:
    return ApplicationCreate.model_validate(
        {
            "coronersLetterId": str(uuid.uuid4()),
            "proceeding": {"proceedingId": "IQOT"},
            "client": {
                "clientFirstName": "Test",
                "clientLastName": "Surname",
                "dateOfBirth": "01-01-1990",
                "correspondenceAddressSource": "USE_SPECIFIED_ADDRESS",
                "correspondenceAddress": {
                    "addressLine1": "2 Example Lane",
                    "townOrCity": "London",
                    "postcode": "SW1A 1AA",
                },
                "hasNoFixedAbode": False,
                "homeAddress": {
                    "addressLine1": "1 Example Lane",
                    "townOrCity": "London",
                    "postcode": "SW1A 1AA",
                },
                "isClientCorrespondenceRecipient": True,
            },
            "publicBodies": [{"publicBodyId": "Department for Transport"}],
            "deceased": {
                "deceasedFirstName": "Test",
                "deceasedLastName": "Surname",
                "deceasedDateOfBirth": "01-01-2000",
                "deceasedDateOfDeath": "01-01-2025",
                "coronersReference": "COR-2025-001",
                "clientRelationshipToDeceased": "guardian",
            },
            "provider": {
                "officeId": "001",
                "emailAddress": email_address,
            },
        }
    )


def test_execute_creates_application_sends_confirmation_email_and_commits():
    request = _make_request()
    application = create_base_application()
    create_application_port = MagicMock(spec=CreateApplicationPort)
    create_application_port.create_application.return_value = application
    create_history_event_port = MagicMock(spec=CreateHistoryEventPort)
    gov_notify_port = MagicMock(spec=GovNotifyPort)

    use_case = CreateApplicationUseCase(
        create_application_port=create_application_port,
        create_history_event_port=create_history_event_port,
        gov_notify_port=gov_notify_port,
    )

    result = use_case.execute(request, "0A123B")

    assert result == application
    create_application_port.create_application.assert_called_once_with(
        request, "0A123B"
    )
    create_history_event_port.create_history_event.assert_called_once_with(
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        actor="provider@example.com",
        actor_type=ActorType.PROVIDER,
        event_description="Application received",
        laa_reference=application.laa_reference,
        event_data=None,
    )
    gov_notify_port.send_application_submit_confirmation_email.assert_called_once_with(
        application,
        "provider@example.com",
    )
    create_application_port.commit.assert_called_once_with()
    create_history_event_port.commit.assert_called_once_with()
    create_application_port.rollback.assert_not_called()
    create_history_event_port.rollback.assert_not_called()


def test_execute_passes_authenticated_firm_code_to_create_application_port():
    request = _make_request()
    create_application_port = MagicMock(spec=CreateApplicationPort)
    create_application_port.create_application.return_value = create_base_application()
    create_history_event_port = MagicMock(spec=CreateHistoryEventPort)
    gov_notify_port = MagicMock(spec=GovNotifyPort)

    use_case = CreateApplicationUseCase(
        create_application_port=create_application_port,
        create_history_event_port=create_history_event_port,
        gov_notify_port=gov_notify_port,
    )

    use_case.execute(request, "1473")

    create_application_port.create_application.assert_called_once_with(request, "1473")


def test_execute_rolls_back_and_reraises_when_notify_fails():
    request = _make_request()
    create_application_port = MagicMock(spec=CreateApplicationPort)
    create_application_port.create_application.return_value = create_base_application()
    create_history_event_port = MagicMock(spec=CreateHistoryEventPort)
    gov_notify_port = MagicMock(spec=GovNotifyPort)
    gov_notify_port.send_application_submit_confirmation_email.side_effect = (
        RuntimeError("notify failed")
    )

    use_case = CreateApplicationUseCase(
        create_application_port=create_application_port,
        create_history_event_port=create_history_event_port,
        gov_notify_port=gov_notify_port,
    )

    with pytest.raises(RuntimeError, match="notify failed"):
        use_case.execute(request, "0A123B")

    create_application_port.commit.assert_not_called()
    create_history_event_port.commit.assert_not_called()
    create_application_port.rollback.assert_called_once_with()
    create_history_event_port.rollback.assert_called_once_with()


def test_execute_rolls_back_and_reraises_when_commit_fails():
    request = _make_request()
    application = create_base_application()
    create_application_port = MagicMock(spec=CreateApplicationPort)
    create_application_port.create_application.return_value = application
    create_application_port.commit.side_effect = RuntimeError("commit failed")
    create_history_event_port = MagicMock(spec=CreateHistoryEventPort)
    gov_notify_port = MagicMock(spec=GovNotifyPort)

    use_case = CreateApplicationUseCase(
        create_application_port=create_application_port,
        create_history_event_port=create_history_event_port,
        gov_notify_port=gov_notify_port,
    )

    with pytest.raises(RuntimeError, match="commit failed"):
        use_case.execute(request, "0A123B")

    gov_notify_port.send_application_submit_confirmation_email.assert_called_once_with(
        application,
        "provider@example.com",
    )
    create_application_port.rollback.assert_called_once_with()
    create_history_event_port.rollback.assert_called_once_with()
