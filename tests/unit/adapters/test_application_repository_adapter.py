from unittest.mock import MagicMock, call

import pytest
from sqlmodel import select

from app.adapters.application_repository_adapter import ApplicationRepositoryAdapter
from app.models.application.enums import (
    AddressSource,
    CorrespondenceRecipientType,
    ProceedingId,
    PublicBodyId,
)
from app.models.application.index import (
    Application,
    ApplicationCreate,
    ApplicationProceeding,
)


def _make_request(with_addresses: bool = True) -> ApplicationCreate:
    client = {
        "clientFirstName": "Test",
        "clientLastName": "Surname",
        "dateOfBirth": "01-01-1990",
        "correspondenceAddressSource": "USE_SPECIFIED_ADDRESS",
        "hasNoFixedAbode": False,
        "homeAddress": {
            "addressLine1": "1 Example Lane",
            "townOrCity": "London",
            "postcode": "SW1A 1AA",
        },
        "isClientCorrespondenceRecipient": False,
        "correspondenceRecipient": {
            "recipientType": "ORGANISATION",
            "recipientName": "Inquests Support Org",
        },
    }

    if with_addresses:
        client["correspondenceAddress"] = {
            "addressLine1": "2 Example Lane",
            "townOrCity": "London",
            "postcode": "SW1A 1AA",
        }
    else:
        client["correspondenceAddressSource"] = "USE_PROVIDER_ADDRESS"
        client["hasNoFixedAbode"] = True
        client.pop("homeAddress")

    return ApplicationCreate.model_validate(
        {
            "coronersLetterId": "test-file_abc123.pdf",
            "proceedings": [{"proceedingId": "TEST1"}],
            "client": client,
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
                "emailAddress": "provider@example.com",
            },
        }
    )


def test_get_application_by_laa_reference_returns_existing_application(session):
    test_app_reference = session.exec(select(Application)).first().laa_reference
    adapter = ApplicationRepositoryAdapter(session)

    result = adapter.get_application_by_laa_reference(
        str(test_app_reference.laa_reference)
    )

    assert result is not None
    assert result.laa_reference == test_app_reference.laa_reference


def test_list_applications_returns_all_applications(session):
    test_applications = session.exec(select(Application)).all()
    adapter = ApplicationRepositoryAdapter(session)

    result = adapter.list_applications()

    assert len(result) == len(test_applications)


def test_create_application_persists_application_and_nested_data(session):
    request = _make_request(with_addresses=True)
    adapter = ApplicationRepositoryAdapter(session)

    initial_count = len(session.exec(select(Application)).all())
    created_application = adapter.create_application(request)
    stored_application = session.get(Application, created_application.laa_reference)

    assert created_application.laa_reference is not None
    assert len(session.exec(select(Application)).all()) == initial_count + 1
    assert stored_application is not None
    assert (
        stored_application.client.correspondence_address_source
        == AddressSource.USE_SPECIFIED_ADDRESS
    )
    assert (
        stored_application.client.correspondence_recipient_type
        == CorrespondenceRecipientType.ORGANISATION
    )
    assert (
        stored_application.client.correspondence_recipient_name
        == "Inquests Support Org"
    )
    assert stored_application.client.home_address_id is not None
    assert stored_application.client.correspondence_address_id is not None
    assert stored_application.proceedings[0].proceeding_id == ProceedingId.TEST1
    assert (
        stored_application.public_bodies[0].public_body_id
        == PublicBodyId.DEPARTMENT_FOR_TRANSPORT
    )
    assert stored_application.provider.email_address == "provider@example.com"
    assert stored_application.coroners_letter.sds_id == "test-file_abc123.pdf"


def test_create_application_handles_request_without_home_or_correspondence_address(
    session,
):
    request = _make_request(with_addresses=False)
    adapter = ApplicationRepositoryAdapter(session)

    created_application = adapter.create_application(request)
    stored_application = session.get(Application, created_application.laa_reference)

    assert stored_application is not None
    assert (
        stored_application.client.correspondence_address_source
        == AddressSource.USE_PROVIDER_ADDRESS
    )
    assert stored_application.client.home_address_id is None
    assert stored_application.client.correspondence_address_id is None


def test_commit_delegates_to_session_commit():
    mock_session = MagicMock()
    adapter = ApplicationRepositoryAdapter(mock_session)

    adapter.commit()

    mock_session.commit.assert_called_once_with()


def test_rollback_delegates_to_session_rollback():
    mock_session = MagicMock()
    adapter = ApplicationRepositoryAdapter(mock_session)

    adapter.rollback()

    mock_session.rollback.assert_called_once_with()


def test_persist_merits_decision_adds_entities_and_commits():
    mock_session = MagicMock()
    adapter = ApplicationRepositoryAdapter(mock_session)
    application = Application(laa_reference=1, deceased_id=1, provider_id=1)
    proceeding = ApplicationProceeding(
        laa_reference=1, proceeding_id=ProceedingId.TEST1
    )

    adapter.persist_merits_decision(application, proceeding)

    assert mock_session.add.call_args_list == [call(application), call(proceeding)]
    mock_session.commit.assert_called_once_with()
    mock_session.rollback.assert_not_called()


def test_persist_merits_decision_rolls_back_and_reraises_when_commit_fails():
    mock_session = MagicMock()
    mock_session.commit.side_effect = RuntimeError("database failure")
    adapter = ApplicationRepositoryAdapter(mock_session)
    application = Application(laa_reference=1, deceased_id=1, provider_id=1)
    proceeding = ApplicationProceeding(
        laa_reference=1, proceeding_id=ProceedingId.TEST1
    )

    with pytest.raises(RuntimeError, match="database failure"):
        adapter.persist_merits_decision(application, proceeding)

    mock_session.rollback.assert_called_once_with()
