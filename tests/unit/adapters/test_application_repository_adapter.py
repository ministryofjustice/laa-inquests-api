import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, call

import pytest
from sqlmodel import select

from app.adapters.application_repository_adapter import ApplicationRepositoryAdapter
from app.domain.coroners_letter import CoronersLetter
from app.models.application.enums import (
    AddressSource,
    CorrespondenceRecipientType,
    MeritsDecision,
    ProceedingId,
    PublicBodyId,
)
from app.models.application.index import (
    Application,
    ApplicationCreate,
    ApplicationProceeding,
)
from app.models.application.index import (
    CoronersLetter as CoronersLetterModel,
)
from tests.e2e.factories import create_application_in_db


def _make_request(with_addresses: bool = True) -> ApplicationCreate:
    client = {
        "clientFirstName": "Test",
        "clientLastName": "Surname",
        "dateOfBirth": "1990-01-01",
        "correspondenceAddressSource": "USE_SPECIFIED_ADDRESS",
        "hasNoFixedAbode": False,
        "homeAddress": {
            "addressLine1": "1 Example Lane",
            "townOrCity": "London",
            "postcode": "SW1A 1AA",
        },
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
            "coronersLetterId": str(uuid.uuid4()),
            "proceeding": {"proceedingId": "IQOT"},
            "client": client,
            "publicBodies": [{"publicBodyId": "Department for Transport"}],
            "deceased": {
                "deceasedFirstName": "Test",
                "deceasedLastName": "Surname",
                "deceasedDateOfBirth": "2000-01-01",
                "deceasedDateOfDeath": "2025-01-01",
                "coronersReference": "COR-2025-001",
                "clientRelationshipToDeceased": "guardian",
            },
            "provider": {
                "officeId": "0U651L",
                "emailAddress": "provider@example.com",
            },
        }
    )


class TestGetApplicationByLaaReference:
    def test_returns_existing_application(self, session):
        test_app_reference = session.exec(select(Application)).first().laa_reference
        adapter = ApplicationRepositoryAdapter(session)

        result = adapter.get_application_by_laa_reference(str(test_app_reference))

        assert result is not None
        assert result.laa_reference == test_app_reference


class TestListApplications:
    def test_returns_all_applications(self, session):
        test_applications = session.exec(select(Application)).all()
        adapter = ApplicationRepositoryAdapter(session)

        result = adapter.list_applications()

        assert len(result) == len(test_applications)


class TestCreateApplication:
    def test_persists_application_and_nested_data(self, session):
        request = _make_request(with_addresses=True)
        adapter = ApplicationRepositoryAdapter(session)

        initial_count = len(session.exec(select(Application)).all())
        created_application = adapter.create_application(request, "0A123B")
        stored_application = session.get(
            Application, created_application.application_id
        )

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
        assert stored_application.proceeding.proceeding_id == ProceedingId.IQOT
        assert (
            stored_application.public_bodies[0].public_body_id
            == PublicBodyId.DEPARTMENT_FOR_TRANSPORT
        )
        assert stored_application.provider.email_address == "provider@example.com"
        assert stored_application.provider.firm_code == "0A123B"
        assert stored_application.coroners_letter_id == request.coroners_letter_id

    def test_handles_request_without_home_or_correspondence_address(self, session):
        request = _make_request(with_addresses=False)
        adapter = ApplicationRepositoryAdapter(session)

        created_application = adapter.create_application(request, "0A123B")
        stored_application = session.get(
            Application, created_application.application_id
        )

        assert stored_application is not None
        assert (
            stored_application.client.correspondence_address_source
            == AddressSource.USE_PROVIDER_ADDRESS
        )
        assert stored_application.client.home_address_id is None
        assert stored_application.client.correspondence_address_id is None


class TestCommitAndRollback:
    def test_delegates_to_session_commit(self):
        mock_session = MagicMock()
        adapter = ApplicationRepositoryAdapter(mock_session)

        adapter.commit()

        mock_session.commit.assert_called_once_with()

    def test_delegates_to_session_rollback(self):
        mock_session = MagicMock()
        adapter = ApplicationRepositoryAdapter(mock_session)

        adapter.rollback()

        mock_session.rollback.assert_called_once_with()


class TestSaveUploadedCoronersLetter:
    def test_persists_and_commits(self):
        mock_session = MagicMock()
        adapter = ApplicationRepositoryAdapter(mock_session)
        coroners_letter = CoronersLetter(
            sds_file_name="sds-file.pdf",
            file_name="upload.pdf",
        )

        result = adapter.save_uploaded_coroners_letter(coroners_letter)

        mock_session.add.assert_called_once()
        saved_model = mock_session.add.call_args[0][0]
        assert isinstance(saved_model, CoronersLetterModel)
        assert saved_model.sds_file_name == coroners_letter.sds_file_name
        assert saved_model.file_name == coroners_letter.file_name
        mock_session.flush.assert_called_once_with()
        mock_session.commit.assert_called_once_with()
        assert result == saved_model.coroners_letter_id


class TestUpdateDecision:
    def test_adds_entities_and_commits(self):
        mock_session = MagicMock()
        adapter = ApplicationRepositoryAdapter(mock_session)
        proceeding = ApplicationProceeding(
            application_id=1, proceeding_id=ProceedingId.IQOT
        )

        adapter.update_decision(proceeding)

        assert mock_session.add.call_args_list == [call(proceeding)]
        mock_session.flush.assert_called_once_with()
        mock_session.rollback.assert_not_called()


class TestSearchApplications:
    def test_returns_matching_application(self, session):
        test_app_reference = session.exec(select(Application)).first().laa_reference
        adapter = ApplicationRepositoryAdapter(session)

        result = adapter.search_applications(
            str(test_app_reference), "0A123B", frozenset(["0U651L"])
        )

        assert len(result) == 1
        assert result[0].laa_reference == test_app_reference

    def test_returns_empty_list_when_application_is_pending(self, session):
        app = session.exec(select(Application)).first()
        app.proceeding.merits_decision = MeritsDecision.PENDING
        session.add(app.proceeding)
        session.flush()

        adapter = ApplicationRepositoryAdapter(session)

        result = adapter.search_applications(
            str(app.laa_reference),
            "0A123B",
            frozenset(["0U651L"]),
            MeritsDecision.GRANTED,
        )

        assert result == []

    def test_returns_empty_list_when_application_is_refused(self, session):
        app = session.exec(select(Application)).first()
        app.proceeding.merits_decision = MeritsDecision.REFUSED
        session.add(app.proceeding)
        session.flush()

        adapter = ApplicationRepositoryAdapter(session)

        result = adapter.search_applications(
            str(app.laa_reference),
            "0A123B",
            frozenset(["0U651L"]),
            MeritsDecision.GRANTED,
        )

        assert result == []

    def test_returns_pending_application_when_no_merits_filter(self, session):
        app = session.exec(select(Application)).first()
        app.proceeding.merits_decision = MeritsDecision.PENDING
        session.add(app.proceeding)
        session.flush()

        adapter = ApplicationRepositoryAdapter(session)

        result = adapter.search_applications(
            str(app.laa_reference), "0A123B", frozenset(["0U651L"])
        )

        assert len(result) == 1
        assert result[0].laa_reference == app.laa_reference

    def test_returns_empty_list_when_firm_code_does_not_match(self, session):
        test_app_reference = session.exec(select(Application)).first().laa_reference
        adapter = ApplicationRepositoryAdapter(session)

        result = adapter.search_applications(
            str(test_app_reference), "ZZ999Z", frozenset(["0U651L"])
        )

        assert result == []

    def test_returns_empty_list_when_office_id_does_not_match_office_code(
        self, session
    ):
        test_app_reference = session.exec(select(Application)).first().laa_reference
        adapter = ApplicationRepositoryAdapter(session)

        result = adapter.search_applications(
            str(test_app_reference), "0A123B", frozenset(["00AABB"])
        )

        assert result == []

    def test_returns_empty_list_when_office_id_does_not_match_multiple_office_codes(
        self, session
    ):
        test_app_reference = session.exec(select(Application)).first().laa_reference
        adapter = ApplicationRepositoryAdapter(session)

        result = adapter.search_applications(
            str(test_app_reference), "0A123B", frozenset(["00AABB", "00CCDD"])
        )

        assert result == []

    def test_returns_empty_list_for_non_numeric_reference(self, session):
        adapter = ApplicationRepositoryAdapter(session)

        result = adapter.search_applications(
            "NOT-A-NUMBER", "0A123B", frozenset(["0U651L"])
        )

        assert result == []

    def test_returns_empty_list_for_unknown_reference(self, session):
        adapter = ApplicationRepositoryAdapter(session)

        result = adapter.search_applications("99999", "0A123B", frozenset(["0U651L"]))

        assert result == []


class TestGenerateLaaReference:
    def test_returns_unique_reference(self, session):
        adapter = ApplicationRepositoryAdapter(session)

        reference1 = adapter._generate_laa_reference()
        reference2 = adapter._generate_laa_reference()

        assert reference1 != reference2
        assert isinstance(reference1, str)
        assert isinstance(reference2, str)

    def test_does_not_return_ambiguous_characters(self, session):
        adapter = ApplicationRepositoryAdapter(session)

        # Generate multiple references to check for ambiguous characters, due to probabilties.
        # 10 attempts should give >99% chance of catching any issues with ambiguous characters.

        for _ in range(10):
            reference = adapter._generate_laa_reference()
            # Ignore the first 4 characters (INQ-) and check the rest for ambiguous characters
            assert all(char not in reference[4:] for char in "B8G6I10OQDS5Z2")


class TestGetLaaReference:
    def test_does_not_contain_banned_words(self, session):
        adapter = ApplicationRepositoryAdapter(session)

        adapter._generate_laa_reference = MagicMock(
            side_effect=["INQ-XXY-YYY", "INQ-YYY-YYY"]
        )  # First call returns a bad reference, second call returns a good one
        reference = adapter._get_laa_reference()
        assert reference == "INQ-YYY-YYY"
        assert (
            adapter._generate_laa_reference.call_count == 2
        )  # Ensure that it retried after getting a bad reference

    def test_does_not_contain_banned_words_across_hyphens(self, session):
        adapter = ApplicationRepositoryAdapter(session)

        adapter._generate_laa_reference = MagicMock(
            side_effect=["INQ-YYX-XYY", "INQ-YYY-YYY"]
        )  # First call returns a bad reference, second call returns a good one
        reference = adapter._get_laa_reference()
        assert reference == "INQ-YYY-YYY"
        assert (
            adapter._generate_laa_reference.call_count == 2
        )  # Ensure that it retried after getting a bad reference

    def test_does_not_return_existing_reference(self, session):
        adapter = ApplicationRepositoryAdapter(session)

        # Create an application with a specific reference to simulate an existing reference
        existing_reference = "INQ-AAA-AAA"
        create_application_in_db(
            session,
            laa_reference=existing_reference,
        )

        adapter._generate_laa_reference = MagicMock(
            side_effect=[existing_reference, "INQ-YYY-YYY"]
        )  # First call returns an existing reference, second call returns a new one
        reference = adapter._get_laa_reference()
        assert reference == "INQ-YYY-YYY"
        assert (
            adapter._generate_laa_reference.call_count == 2
        )  # Ensure that it retried after getting an existing reference

    def test_raises_error_after_max_attempts(self, session):
        adapter = ApplicationRepositoryAdapter(session)

        # Mock _generate_laa_reference to always return a banned word
        adapter._generate_laa_reference = MagicMock(return_value="INQ-XXX-XXX")

        with pytest.raises(RuntimeError) as exc_info:
            adapter._get_laa_reference()
        assert (
            str(exc_info.value)
            == "Maximum attempts reached for generating LAA reference"
        )


class TestGetPendingApplications:
    def test_returns_applications_with_pending_decision(self, session):
        app = session.exec(select(Application)).first()
        app.proceeding.merits_decision = MeritsDecision.PENDING
        session.add(app.proceeding)
        session.flush()

        adapter = ApplicationRepositoryAdapter(session)

        result = adapter.get_pending_applications()

        assert len(result) == 1
        assert result[0].proceeding.merits_decision == "PENDING"

    def test_excludes_granted_applications(self, session):
        app = session.exec(select(Application)).first()
        app.proceeding.merits_decision = MeritsDecision.GRANTED
        session.add(app.proceeding)
        session.flush()

        adapter = ApplicationRepositoryAdapter(session)

        result = adapter.get_pending_applications()

        assert len(result) == 0

    def test_excludes_refused_applications(self, session):
        app = session.exec(select(Application)).first()
        app.proceeding.merits_decision = MeritsDecision.REFUSED
        session.add(app.proceeding)
        session.flush()

        adapter = ApplicationRepositoryAdapter(session)

        result = adapter.get_pending_applications()

        assert len(result) == 0

    def test_ordered_by_created_at_ascending(self, session):
        app = session.exec(select(Application)).first()
        app.proceeding.merits_decision = MeritsDecision.PENDING
        session.add(app.proceeding)
        session.flush()

        older_app = create_application_in_db(
            session,
            created_at=datetime(2019, 1, 1, tzinfo=UTC),
        )

        adapter = ApplicationRepositoryAdapter(session)

        result = adapter.get_pending_applications()

        assert len(result) == 2
        assert result[0].laa_reference == older_app.laa_reference


class TestUpdateApplicationPublicBodies:
    def test_updates_to_single_public_body_and_commits(self, session):
        application = session.exec(select(Application)).first()
        adapter = ApplicationRepositoryAdapter(session)

        new_public_bodies = [PublicBodyId.MINISTRY_OF_DEFENCE]
        adapter.update_public_bodies(application, new_public_bodies)

        updated_app = session.get(Application, application.application_id)
        assert len(updated_app.public_bodies) == 1
        assert (
            updated_app.public_bodies[0].public_body_id
            == PublicBodyId.MINISTRY_OF_DEFENCE
        )

    def test_updates_to_the_same_single_public_body_and_commits(self, session):
        application = session.exec(select(Application)).first()
        adapter = ApplicationRepositoryAdapter(session)

        new_public_bodies = [PublicBodyId.DEPARTMENT_FOR_TRANSPORT]
        adapter.update_public_bodies(application, new_public_bodies)

        updated_app = session.get(Application, application.application_id)
        assert len(updated_app.public_bodies) == 1
        assert (
            updated_app.public_bodies[0].public_body_id
            == PublicBodyId.DEPARTMENT_FOR_TRANSPORT
        )

    def test_updates_to_multiple_public_bodies_and_commits(self, session):
        application = session.exec(select(Application)).first()
        adapter = ApplicationRepositoryAdapter(session)

        new_public_bodies = [
            PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
            PublicBodyId.MINISTRY_OF_DEFENCE,
        ]
        adapter.update_public_bodies(application, new_public_bodies)

        updated_app = session.get(Application, application.application_id)

        assert len(updated_app.public_bodies) == 2
        assert {pb.public_body_id for pb in updated_app.public_bodies} == set(
            new_public_bodies
        )
