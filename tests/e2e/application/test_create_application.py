import uuid
from unittest.mock import MagicMock

import pytest
from sqlmodel import select

from app import api
from app.auth.rbac import Permission, Role, get_current_user_permissions
from app.models.application.index import Application, DuplicateApplicationRecord
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent
from app.routers.applications import get_provider_details_port
from app.routers.dependencies.entra_auth import get_current_provider_office_codes
from app.use_cases.exceptions import ProviderOfficeNotFoundError

pytestmark = pytest.mark.usefixtures("mock_gov_notify")


def _make_request_body(client_overrides=None):
    client = {
        "clientFirstName": "Test",
        "clientLastName": "Surname",
        "dateOfBirth": "1990-01-01",
        "nationalInsuranceNumber": "AB12345A",
        "correspondenceAddressSource": "USE_SPECIFIED_ADDRESS",
        "correspondenceAddress": {
            "addressLine1": "2 Example Lane",
            "townOrCity": "London",
            "postcode": "SW1A 1AA",
        },
        "hasNoFixedAbode": False,
        "homeAddress": {
            "addressLine1": "1 Example Lane",
            "addressLine2": "Flat 2",
            "townOrCity": "London",
            "county": "Greater London",
            "postcode": "SW1A 1AA",
        },
    }
    if client_overrides:
        client.update(client_overrides)
    return {
        "coronersLetterId": str(uuid.uuid4()),
        "proceeding": {"proceedingId": "IQ042"},
        "client": client,
        "publicBodies": [{"publicBodyId": "Department for Transport"}],
        "deceased": {
            "deceasedFirstName": "Test",
            "deceasedLastName": "Surname",
            "deceasedDateOfBirth": "2000-01-01",
            "deceasedDateOfDeath": "2025-01-01",
            "coronersReference": "COR-2025-001",
            "furtherInformation": "Further details to be confirmed",
            "clientRelationshipToDeceased": "guardian",
        },
        "provider": {
            "officeId": "0U651L",
            "emailAddress": "provider@example.com",
        },
    }


PERSON_NAME_CLIENT_FIELDS = [
    "clientFirstName",
    "clientLastName",
    "clientLastNameAtBirth",
]

RECIPIENT_TYPES = ["PERSON", "ORGANISATION"]

DECEASED_FIELDS = [
    "deceasedFirstName",
    "deceasedLastName",
    "coronersReference",
    "clientRelationshipToDeceased",
]

ADDRESS_KEYS = ["homeAddress", "correspondenceAddress"]
ADDRESS_FIELDS = ["addressLine1", "addressLine2", "townOrCity", "county"]


def _set_client_name_field(body, field, value):
    body["client"][field] = value


def _set_recipient(body, recipient_type, name):
    body["client"]["correspondenceRecipient"] = {
        "recipientType": recipient_type,
        "recipientName": name,
    }


class TestCreateApplication:
    def test_201_create_application_response_contains_expected_base_properties(
        self, client
    ):
        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )
        assert response.status_code == 201
        new_application = response.json()
        assert isinstance(new_application["laaReference"], str)
        assert isinstance(new_application["createdAt"], str)
        assert isinstance(new_application["updatedAt"], str)
        assert isinstance(new_application["status"], str)
        assert isinstance(new_application["usedDelegatedFunctions"], bool)
        assert isinstance(new_application["applicationType"], str)
        assert isinstance(new_application["autoGrant"], bool)
        assert isinstance(new_application["overallDecision"], str)
        assert isinstance(new_application["proceeding"], dict)

    def test_201_create_application_response_contains_expected_proceeding_information(
        self, client
    ):
        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )
        new_application = response.json()
        proceeding = new_application["proceeding"]
        assert proceeding["proceedingId"] == "IQ042"
        assert proceeding["categoryOfLaw"] == "INQUESTS"
        assert proceeding["matterType"] == "INQUESTS"
        assert proceeding["levelOfService"] == "FULL_REPRESENTATION"
        assert proceeding["certificateType"] == "SUBSTANTIVE"
        assert proceeding["clientInvolvementType"] == "RESPONDENT"
        assert proceeding["meritsDecision"] == "SUBMITTED"
        assert proceeding["substantiveCostLimitation"] == 0
        assert isinstance(proceeding["scopeDescription"], str)
        assert isinstance(proceeding["proceedingName"], str)
        assert isinstance(proceeding["proceedingDescription"], str)

    def test_201_responds_with_expected_client_details(self, client):
        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )
        new_application = response.json()
        client_data = new_application["client"]
        assert isinstance(client_data["clientId"], int)
        assert client_data["clientFirstName"] == "Test"
        assert client_data["clientLastName"] == "Surname"
        assert client_data["clientLastNameAtBirth"] is None
        assert client_data["dateOfBirth"] == "1990-01-01"
        assert client_data["nationalInsuranceNumber"] == "AB12345A"
        assert client_data["correspondenceAddressSource"] == "USE_SPECIFIED_ADDRESS"
        assert client_data["correspondenceAddress"] == {
            "addressLine1": "2 Example Lane",
            "addressLine2": None,
            "townOrCity": "London",
            "county": None,
            "postcode": "SW1A 1AA",
        }
        assert new_application["client"]["correspondenceRecipient"] is None
        assert client_data["homeAddress"] == {
            "addressLine1": "1 Example Lane",
            "addressLine2": "Flat 2",
            "townOrCity": "London",
            "county": "Greater London",
            "postcode": "SW1A 1AA",
        }
        assert not client_data["hasAppliedPreviously"]

    def test_201_create_application_stores_authenticated_users_firm_code(
        self, client, session
    ):
        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201
        laa_reference = response.json()["laaReference"]
        application = session.exec(
            select(Application).where(Application.laa_reference == laa_reference)
        ).one()
        assert application.provider.firm_code == "0A123B"

    def test_201_create_application_creates_history_event(self, client, session):
        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201
        laa_reference = response.json()["laaReference"]
        application = session.exec(
            select(Application).where(Application.laa_reference == laa_reference)
        ).one()

        history_event = session.exec(
            select(HistoryEvent).where(
                (HistoryEvent.application_id == application.application_id)
                & (
                    HistoryEvent.event_reference
                    == HistoryEventReference.APPLICATION_SUBMITTED
                )
            )
        ).one()

        assert (
            history_event.event_reference == HistoryEventReference.APPLICATION_SUBMITTED
        )
        assert history_event.actor == "provider@example.com"
        assert history_event.actor_type == ActorType.PROVIDER
        assert history_event.event_data is None
        assert history_event.application_id == application.application_id

    def test_201_create_application_creates_duplicate_records(self, client, session):
        first_application_id = (
            session.exec(select(Application).order_by(Application.created_at.desc()))
            .first()
            .application_id
        )

        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201
        laa_reference = response.json()["laaReference"]

        application_id = (
            session.exec(
                select(Application).where(Application.laa_reference == laa_reference)
            )
            .one()
            .application_id
        )

        duplicate_records = session.exec(
            select(DuplicateApplicationRecord)
            .where(DuplicateApplicationRecord.application_id == application_id)
            .where(
                DuplicateApplicationRecord.duplicate_application_id
                == first_application_id
            )
        ).all()

        assert len(duplicate_records) == 1
        assert response.json()["potentialDuplicateApplications"] is None

    def test_201_create_application_can_omit_correspondence_address(self, client):
        request_body = _make_request_body(
            {"correspondenceAddressSource": "USE_CLIENT_HOME_ADDRESS"}
        )
        request_body["client"].pop("correspondenceAddress")

        response = client.post(
            "/applications",
            json=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201
        client_details = response.json()["client"]
        assert (
            client_details["correspondenceAddressSource"] == "USE_CLIENT_HOME_ADDRESS"
        )
        assert client_details["correspondenceAddress"] is None

    def test_201_create_application_responds_with_expected_public_body_details(
        self, client
    ):
        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )
        new_application = response.json()
        assert len(new_application["publicBodies"]) == 1
        public_body = new_application["publicBodies"][0]
        assert public_body["publicBodyDescription"] == "Department for Transport"

    def test_201_create_application_response_includes_deceased_details(self, client):
        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )
        new_application = response.json()
        deceased = new_application["deceased"]
        assert isinstance(deceased["deceasedId"], int)
        assert deceased["deceasedFirstName"] == "Test"
        assert deceased["deceasedLastName"] == "Surname"
        assert deceased["deceasedDateOfBirth"] == "2000-01-01"
        assert deceased["deceasedDateOfDeath"] == "2025-01-01"
        assert deceased["coronersReference"] == "COR-2025-001"
        assert deceased["furtherInformation"] == "Further details to be confirmed"
        assert deceased["clientRelationshipToDeceased"] == "guardian"

    def test_201_create_application_response_contains_coroners_letter(self, client):
        upload_response = client.post(
            "/applications/upload-coroners-letter",
            data={"office_id": "0U651L"},
            files={
                "file": (
                    "test-file_abc123.pdf",
                    b"test content",
                    "application/pdf",
                )
            },
            headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
        )
        assert upload_response.status_code == 201
        coroners_letter_id = upload_response.json()["coronersLetterId"]

        body = _make_request_body()
        body["coronersLetterId"] = coroners_letter_id

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )
        assert response.status_code == 201
        new_application = response.json()
        assert new_application["coronersLetter"] is not None
        assert new_application["coronersLetter"]["fileName"] == "test-file_abc123.pdf"

    def test_422_rejected_when_has_no_fixed_abode_is_false_and_home_address_is_absent(
        self, client
    ):
        body = _make_request_body(
            {
                "correspondenceAddressSource": "USE_CLIENT_HOME_ADDRESS",
                "homeAddress": None,
            }
        )
        del body["client"]["correspondenceAddress"]

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 422

    def test_422_rejected_when_has_no_fixed_abode_is_true_and_home_address_is_provided(
        self, client
    ):
        body = _make_request_body({"hasNoFixedAbode": True})

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 422

    @pytest.mark.parametrize("field", ["clientFirstName", "clientLastName"])
    @pytest.mark.parametrize("value", ["=cmd", "+1", "-1", "@SUM(A1)", " =cmd"])
    def test_422_rejected_when_client_name_starts_with_formula_trigger(
        self, client, field, value
    ):
        body = _make_request_body({field: value})

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 422

    @pytest.mark.parametrize("field", PERSON_NAME_CLIENT_FIELDS)
    @pytest.mark.parametrize(
        "value",
        [
            "zxdfsdfdszxdfsdfds'';!--\"=&{()}",
            "<Test>",
            "Smith1",
            "a=b",
            "Sm\nith",
            "A" * 101,
            "",
            " ",
        ],
    )
    def test_422_rejected_when_client_name_field_contains_disallowed_input(
        self, client, field, value
    ):
        body = _make_request_body()
        _set_client_name_field(body, field, value)

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 422

    @pytest.mark.parametrize("field", PERSON_NAME_CLIENT_FIELDS)
    @pytest.mark.parametrize(
        "value",
        ["O'Donald", "Smith-Jones", "De Souza", "Siân", "Gŵyn", "A" * 100],
    )
    def test_201_accepts_client_name_field_with_allowed_characters(
        self, client, field, value
    ):
        body = _make_request_body()
        _set_client_name_field(body, field, value)

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (" Jane ", "Jane"),
            ("Jane\n", "Jane"),
            ("O\u2019Brien", "O'Brien"),
            ("Jose\u0301", "Jos\u00e9"),
        ],
    )
    def test_201_stores_names_trimmed_and_normalised(self, client, value, expected):
        body = _make_request_body({"clientFirstName": value})
        body["deceased"]["deceasedFirstName"] = value

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201
        assert response.json()["client"]["clientFirstName"] == expected
        assert response.json()["deceased"]["deceasedFirstName"] == expected

    @pytest.mark.parametrize("recipient_type", RECIPIENT_TYPES)
    @pytest.mark.parametrize(
        "value",
        [
            "zxdfsdfdszxdfsdfds'';!--\"=&{()}",
            "<Test>",
            "Smith;",
            "Smith/Jones",
            "Sm\nith",
            "&&",
            "A" * 101,
            "",
            " ",
        ],
    )
    def test_422_rejected_when_recipient_name_contains_disallowed_input(
        self, client, recipient_type, value
    ):
        body = _make_request_body()
        _set_recipient(body, recipient_type, value)

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 422

    @pytest.mark.parametrize("recipient_type", RECIPIENT_TYPES)
    @pytest.mark.parametrize(
        "value",
        [
            "Smith & Co. Solicitors, Ltd",
            "O'Brien-Jones",
            "Siân Jones",
            "Acme 24 Ltd",
            "A" * 100,
        ],
    )
    def test_201_accepts_person_and_organisation_recipient_names(
        self, client, recipient_type, value
    ):
        body = _make_request_body()
        _set_recipient(body, recipient_type, value)

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201
        assert (
            response.json()["client"]["correspondenceRecipient"]["recipientType"]
            == recipient_type
        )

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (" Smith & Co. ", "Smith & Co."),
            ("O\u2019Brien & Sons", "O'Brien & Sons"),
        ],
    )
    def test_201_stores_recipient_name_trimmed_and_normalised(
        self, client, value, expected
    ):
        body = _make_request_body()
        _set_recipient(body, "ORGANISATION", value)

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201
        recipient = response.json()["client"]["correspondenceRecipient"]
        assert recipient["recipientName"] == expected

    @pytest.mark.parametrize("address_key", ADDRESS_KEYS)
    @pytest.mark.parametrize("field", ADDRESS_FIELDS)
    @pytest.mark.parametrize(
        "value",
        [
            "zxdfsdfdszxdfsdfds'';!--\"=&{()}",
            "<Test>",
            "Lon;don",
            "Lon\ndon",
            "",
            " ",
        ],
    )
    def test_422_rejected_when_address_field_contains_disallowed_input(
        self, client, address_key, field, value
    ):
        body = _make_request_body()
        body["client"][address_key][field] = value

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 422

    @pytest.mark.parametrize("address_key", ADDRESS_KEYS)
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("addressLine1", "A"),
            ("addressLine1", "A" * 101),
            ("addressLine2", "A"),
            ("addressLine2", "A" * 101),
            ("townOrCity", "A"),
            ("townOrCity", "A" * 101),
            ("county", "AB"),
            ("county", "A" * 51),
            ("townOrCity", "London1"),
            ("county", "Kent1"),
        ],
    )
    def test_422_rejected_when_address_field_breaks_its_length_or_character_rules(
        self, client, address_key, field, value
    ):
        body = _make_request_body()
        body["client"][address_key][field] = value

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 422

    @pytest.mark.parametrize("address_key", ADDRESS_KEYS)
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("addressLine1", "123 Example Street"),
            ("addressLine1", "Flat 1/2, O'Neill-Court."),
            ("addressLine1", "Smith & Sons"),
            ("addressLine1", "A" * 100),
            ("addressLine2", "Flat 2"),
            ("addressLine2", "A" * 100),
            ("townOrCity", "London"),
            ("townOrCity", "Stoke-on-Trent"),
            ("townOrCity", "King's Lynn"),
            ("townOrCity", "A" * 100),
            ("county", "Kent"),
            ("county", "Greater London"),
            ("county", "A" * 50),
        ],
    )
    def test_201_accepts_address_field_with_allowed_characters(
        self, client, address_key, field, value
    ):
        body = _make_request_body()
        body["client"][address_key][field] = value

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201

    @pytest.mark.parametrize("address_key", ADDRESS_KEYS)
    @pytest.mark.parametrize(
        ("field", "value", "expected"),
        [
            ("addressLine1", " 1 High Street\n", "1 High Street"),
            ("addressLine1", "O\u2019Neill Court", "O'Neill Court"),
            ("townOrCity", " London ", "London"),
            ("county", "Kent\n", "Kent"),
        ],
    )
    def test_201_stores_address_fields_trimmed_and_normalised(
        self, client, address_key, field, value, expected
    ):
        body = _make_request_body()
        body["client"][address_key][field] = value

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201
        assert response.json()["client"][address_key][field] == expected

    @pytest.mark.parametrize("field", DECEASED_FIELDS)
    @pytest.mark.parametrize(
        "value",
        [
            "zxdfsdfdszxdfsdfds'';!--\"=&{()}",
            "<Spousezxdfsdfds'';!--\"=&{()}>",
            "<Test>",
            "Sm\nith",
        ],
    )
    def test_422_rejected_when_deceased_field_contains_disallowed_input(
        self, client, field, value
    ):
        body = _make_request_body()
        body["deceased"][field] = value

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 422

    @pytest.mark.parametrize(
        ("field", "too_long"),
        [
            ("deceasedFirstName", "A" * 101),
            ("deceasedLastName", "A" * 101),
            ("coronersReference", "A" * 51),
            ("clientRelationshipToDeceased", "A" * 71),
        ],
    )
    def test_422_rejected_when_deceased_field_exceeds_its_limit(
        self, client, field, too_long
    ):
        body = _make_request_body()
        body["deceased"][field] = too_long

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 422

    @pytest.mark.parametrize("field", ["deceasedFirstName", "deceasedLastName"])
    @pytest.mark.parametrize("value", ["", " ", "Smith1", "-Smith"])
    def test_422_rejected_when_deceased_name_is_empty_or_not_letters(
        self, client, field, value
    ):
        body = _make_request_body()
        body["deceased"][field] = value

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 422

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("deceasedFirstName", "O'Donald"),
            ("deceasedLastName", "Smith-Jones"),
            ("deceasedLastName", "De Souza"),
            ("deceasedLastName", "García"),
            ("deceasedFirstName", "A" * 100),
            ("coronersReference", "COR-2025/123.A"),
            ("coronersReference", "A" * 50),
            ("clientRelationshipToDeceased", "Son"),
            ("clientRelationshipToDeceased", "Step-parent"),
            ("clientRelationshipToDeceased", "A" * 70),
        ],
    )
    def test_201_accepts_deceased_field_with_allowed_characters(
        self, client, field, value
    ):
        body = _make_request_body()
        body["deceased"][field] = value

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201

    @pytest.mark.parametrize(
        "field", ["coronersReference", "clientRelationshipToDeceased"]
    )
    def test_201_accepts_empty_string_when_no_coroners_reference_or_relationship(
        self, client, field
    ):
        body = _make_request_body()
        body["deceased"][field] = ""

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201

    @pytest.mark.parametrize(
        "value",
        ["<script>alert(1)</script>", "a > b", "bad\x00value", "bad\x1bvalue"],
    )
    def test_422_rejected_when_further_information_contains_disallowed_characters(
        self, client, value
    ):
        body = _make_request_body()
        body["deceased"]["furtherInformation"] = value

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 422

    @pytest.mark.parametrize(
        "value",
        [
            'It\'s "quoted"; see = A1 -- fine & (ok) {yes}',
            "Line one\nLine two",
            "",
            None,
        ],
    )
    def test_201_accepts_further_information_with_quotes_semicolons_and_newlines(
        self, client, value
    ):
        body = _make_request_body()
        body["deceased"]["furtherInformation"] = value

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201

    def test_422_rejected_when_deceased_date_of_death_is_before_date_of_birth(
        self, client
    ):
        body = _make_request_body()
        body["deceased"]["deceasedDateOfBirth"] = "2025-01-02"
        body["deceased"]["deceasedDateOfDeath"] = "2025-01-01"

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 422
        assert (
            "deceased_date_of_death must not be before deceased_date_of_birth"
            in response.text
        )

    def test_201_accepted_when_deceased_date_of_death_equals_date_of_birth(
        self, client
    ):
        body = _make_request_body()
        body["deceased"]["deceasedDateOfBirth"] = "2025-01-01"
        body["deceased"]["deceasedDateOfDeath"] = "2025-01-01"

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201

    def test_201_accepted_when_has_no_fixed_abode_is_true_and_no_home_address_provided(
        self, client
    ):
        body = _make_request_body(
            {
                "hasNoFixedAbode": True,
                "correspondenceAddressSource": "USE_SPECIFIED_ADDRESS",
            }
        )
        body["client"].pop("homeAddress")

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201
        client_data = response.json()["client"]
        assert client_data["hasNoFixedAbode"] is True
        assert client_data["homeAddress"] is None

    def test_201_accepted_when_has_no_fixed_abode_is_false_and_home_address_is_provided(
        self, client
    ):
        response = client.post(
            "/applications",
            json=_make_request_body({"hasNoFixedAbode": False}),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201
        client_data = response.json()["client"]
        assert client_data["hasNoFixedAbode"] is False
        assert client_data["homeAddress"] is not None
        assert client_data["homeAddress"]["addressLine1"] == "1 Example Lane"

    def test_201_create_application_includes_explicit_correspondence_recipient(
        self, client
    ):
        body = _make_request_body()
        body["client"]["correspondenceRecipient"] = {
            "recipientType": "ORGANISATION",
            "recipientName": "Inquests Support Org",
        }

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201
        assert response.json()["client"]["correspondenceRecipient"] == {
            "recipientType": "ORGANISATION",
            "recipientName": "Inquests Support Org",
        }

    def test_201_create_application_response_none_potential_duplicate_applications(
        self, client
    ):
        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201
        assert response.json()["potentialDuplicateApplications"] is None

    def test_201_create_application_response_includes_provider_email(self, client):
        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 201
        assert response.json()["provider"]["emailAddress"] == "provider@example.com"

    def test_403_create_application_forbidden_when_provider_cant_access_office(
        self, client
    ):
        body = _make_request_body()

        def get_current_provider_office_codes_override():
            return ["1"]

        api.dependency_overrides[get_current_provider_office_codes] = (
            get_current_provider_office_codes_override
        )

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 403

    def test_404_create_application_rejected_when_office_not_found(self, client):
        def get_provider_details_port_override():
            mock_port = MagicMock()
            mock_port.get_firm_name.side_effect = ProviderOfficeNotFoundError(
                "Office 0U651L details not found for firm 0A123B"
            )
            return mock_port

        api.dependency_overrides[get_provider_details_port] = (
            get_provider_details_port_override
        )

        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 404

    def test_422_create_application_rejected_when_provider_email_missing(self, client):
        body = _make_request_body()
        del body["provider"]["emailAddress"]

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 422

    def test_422_create_application_fails_without_provider(self, client):
        body = _make_request_body()
        del body["provider"]

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 422

    def test_422_create_application_fails_without_office_id(self, client):
        body = _make_request_body()
        del body["provider"]["officeId"]

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 422

    def test_422_create_application_rejected_when_proceeding_id_is_invalid(
        self, client
    ):
        body = _make_request_body()
        body["proceeding"] = {"proceedingId": "INVALID"}

        response = client.post(
            "/applications",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 422

    def test_500_create_application_rolls_back_when_gov_notify_fails(
        self, client, session, mock_gov_notify
    ):
        """
        Test that application creation rolls back when GovNotify email sending fails.

        This test verifies the critical requirement that email sending is atomic with
        application creation - if the email fails, the entire transaction must rollback.

        Verifies:
        - 500 response when GovNotify fails
        - Application is NOT created in database
        - Transaction rollback occurs correctly
        """
        initial_count = len(session.exec(select(Application)).all())

        mock_gov_notify.send_application_submit_confirmation_email.side_effect = (
            Exception("GovNotify API unavailable")
        )

        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )

        assert response.status_code == 500
        assert response.json() == {"detail": "An internal server error occurred"}

        final_count = len(session.exec(select(Application)).all())
        assert final_count == initial_count, (
            f"Application was created despite email failure. "
            f"Initial count: {initial_count}, Final count: {final_count}"
        )


class TestCreateApplicationRbac:
    def test_201_create_application_with_provider_application_user_app_role(
        self, client
    ):
        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )
        assert response.status_code == 201

    def test_201_create_application_with_permission_override(self, client):
        def get_current_user_permissions_override():
            return {Permission.APPLICATION_CREATE}

        api.dependency_overrides[get_current_user_permissions] = (
            get_current_user_permissions_override
        )

        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
            },
        )
        assert response.status_code == 201
