from unittest.mock import MagicMock

import pytest

from app.models.application.index import Application, ApplicationCreate
from app.ports.create_application_port import CreateApplicationPort
from app.ports.gov_notify_port import GovNotifyPort
from app.use_cases.create_application import CreateApplicationUseCase


def _make_request(email_address: str = "provider@example.com") -> ApplicationCreate:
    return ApplicationCreate.model_validate(
        {
            "coronersLetterId": "test-file_abc123.pdf",
            "proceedings": [{"proceedingId": "TEST1"}],
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
                "firmCode": "0A123B",
                "officeId": "001",
                "emailAddress": email_address,
            },
        }
    )


def _make_application() -> Application:
    return Application(laa_reference=12345, deceased_id=1, provider_id=1)


def test_execute_creates_application_sends_confirmation_email_and_commits():
    request = _make_request()
    application = _make_application()
    create_application_port = MagicMock(spec=CreateApplicationPort)
    create_application_port.create_application.return_value = application
    gov_notify_port = MagicMock(spec=GovNotifyPort)

    use_case = CreateApplicationUseCase(
        create_application_port=create_application_port,
        gov_notify_port=gov_notify_port,
    )

    result = use_case.execute(request)

    assert result == application
    create_application_port.create_application.assert_called_once_with(request)
    gov_notify_port.send_application_submit_confirmation_email.assert_called_once_with(
        application,
        "provider@example.com",
    )
    create_application_port.commit.assert_called_once_with()
    create_application_port.rollback.assert_not_called()


def test_execute_rolls_back_and_reraises_when_notify_fails():
    request = _make_request()
    create_application_port = MagicMock(spec=CreateApplicationPort)
    create_application_port.create_application.return_value = _make_application()
    gov_notify_port = MagicMock(spec=GovNotifyPort)
    gov_notify_port.send_application_submit_confirmation_email.side_effect = (
        RuntimeError("notify failed")
    )

    use_case = CreateApplicationUseCase(
        create_application_port=create_application_port,
        gov_notify_port=gov_notify_port,
    )

    with pytest.raises(RuntimeError, match="notify failed"):
        use_case.execute(request)

    create_application_port.commit.assert_not_called()
    create_application_port.rollback.assert_called_once_with()


def test_execute_rolls_back_and_reraises_when_commit_fails():
    request = _make_request()
    application = _make_application()
    create_application_port = MagicMock(spec=CreateApplicationPort)
    create_application_port.create_application.return_value = application
    create_application_port.commit.side_effect = RuntimeError("commit failed")
    gov_notify_port = MagicMock(spec=GovNotifyPort)

    use_case = CreateApplicationUseCase(
        create_application_port=create_application_port,
        gov_notify_port=gov_notify_port,
    )

    with pytest.raises(RuntimeError, match="commit failed"):
        use_case.execute(request)

    gov_notify_port.send_application_submit_confirmation_email.assert_called_once_with(
        application,
        "provider@example.com",
    )
    create_application_port.rollback.assert_called_once_with()
