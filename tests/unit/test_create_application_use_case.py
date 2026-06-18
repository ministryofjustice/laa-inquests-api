from unittest.mock import MagicMock

from app.models.application.index import (
    Address,
    Application,
    ApplicationCreate,
    Client,
    ClientCreate,
    CoronersLetter,
    CoronersLetterCreate,
    CoronersLetterResponse,
    Deceased,
    DeceasedCreate,
    Provider,
    ProviderCreate,
    ProceedingCreate,
    PublicBodyCreate,
    AddressCreate,
)
from app.use_cases.create_application import CreateApplicationUseCase


def _make_request(client_overrides=None) -> ApplicationCreate:
    client_data = {
        "client_first_name": "Test",
        "client_last_name": "Surname",
        "date_of_birth": "01-01-1990",
        "national_insurance_number": "AB12345A",
        "correspondence_address_source": "USE_SPECIFIED_ADDRESS",
        "correspondence_address": AddressCreate(
            address_line_1="2 Example Lane",
            town_or_city="London",
            postcode="SW1A 1AA",
        ),
        "home_address": AddressCreate(
            address_line_1="1 Example Lane",
            town_or_city="London",
            postcode="SW1A 1AA",
        ),
        "has_no_fixed_abode": False,
        "is_client_correspondence_recipient": True,
    }
    if client_overrides:
        client_data.update(client_overrides)

    return ApplicationCreate(
        coroners_letter=CoronersLetterCreate(
            coroners_letter=b"test coroners letter content",
            file_name="coroners_letter.pdf",
        ),
        proceedings=[ProceedingCreate(proceeding_id="TEST1")],
        client=ClientCreate(**client_data),
        publicBodies=[PublicBodyCreate(public_body_id="Department for Transport")],
        deceased=DeceasedCreate(
            deceased_first_name="Test",
            deceased_last_name="Surname",
            deceased_date_of_birth="01-01-2000",
            deceased_date_of_death="01-01-2025",
            coroners_reference="COR-2025-001",
            further_information="Further details",
            client_relationship_to_deceased="guardian",
        ),
        provider=ProviderCreate(firm_code="0A123B", office_id="001"),
    )


def _make_session() -> MagicMock:
    session = MagicMock()

    def refresh_side_effect(obj):
        if isinstance(obj, Address):
            obj.address_id = 1
        elif isinstance(obj, Client):
            obj.client_id = 1
        elif isinstance(obj, Deceased):
            obj.deceased_id = 1
        elif isinstance(obj, Provider):
            obj.provider_id = 1
        elif isinstance(obj, CoronersLetter):
            obj.coroners_letter_id = 1
        elif isinstance(obj, Application):
            obj.laa_reference = 1

    session.refresh.side_effect = refresh_side_effect
    return session


def _make_coroners_letter_response() -> CoronersLetterResponse:
    return CoronersLetterResponse(
        id="sds-abc123",
        status=201,
        file_name="letter.pdf",
    )


def test_execute_returns_application_when_letter_save_succeeds():
    session = _make_session()
    use_case = CreateApplicationUseCase(session=session)

    result = use_case.execute(_make_request(), _make_coroners_letter_response())

    assert isinstance(result, Application)


def test_execute_handles_no_home_address():
    session = _make_session()
    use_case = CreateApplicationUseCase(session=session)
    request = _make_request(
        {
            "has_no_fixed_abode": True,
            "home_address": None,
            "correspondence_address_source": "USE_SPECIFIED_ADDRESS",
        }
    )

    use_case.execute(request, _make_coroners_letter_response())

    added_objects = [args[0] for args, _ in session.add.call_args_list]
    assert not any(
        isinstance(obj, Address) and not hasattr(obj, "address_line_1")
        for obj in added_objects
    )
    # No home address — correspondence address + client + deceased + provider + coroners_letter + application
    assert session.add.call_count == 6


def test_execute_handles_no_correspondence_address():
    session = _make_session()
    use_case = CreateApplicationUseCase(session=session)
    request = _make_request(
        {
            "correspondence_address_source": "USE_CLIENT_HOME_ADDRESS",
            "correspondence_address": None,
        }
    )

    use_case.execute(request, _make_coroners_letter_response())

    added_objects = [args[0] for args, _ in session.add.call_args_list]
    client_obj = next(obj for obj in added_objects if isinstance(obj, Client))
    assert client_obj.correspondence_address_id is None


def test_execute_saves_coroners_letter_to_db():
    session = _make_session()
    use_case = CreateApplicationUseCase(session=session)

    use_case.execute(_make_request(), _make_coroners_letter_response())

    added_objects = [args[0] for args, _ in session.add.call_args_list]
    letter_obj = next(obj for obj in added_objects if isinstance(obj, CoronersLetter))
    assert letter_obj.sds_id == "sds-abc123"
    assert letter_obj.file_name == "letter.pdf"
