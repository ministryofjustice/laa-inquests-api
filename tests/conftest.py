import pytest
from unittest.mock import MagicMock
from passlib.hash import argon2
from sqlmodel import SQLModel, create_engine, Session, StaticPool
from app import api
from app.db import get_session
from app.db.session import CustomSession
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from app.routers.dependencies import get_entra_auth_port
from app.routers.applications import (
    get_provider_details_port,
    get_gov_notify_port,
    get_sds_port,
    get_pdf_generation_port,
)
from app.models import User
from app.models.application.index import (
    Address,
    Application,
    ApplicationPublicBody,
    Client,
    Deceased,
    Proceeding,
    ProceedingId,
    ApplicationProceeding,
    Provider,
    PublicBody,
    PublicBodyId,
    SDSUploadCoronersLetterResponse,
)

SECRET_KEY = "TEST_KEY"


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    test_session = sessionmaker(
        autocommit=False, autoflush=False, bind=engine, class_=CustomSession
    )
    SQLModel.metadata.create_all(engine)
    users_to_add = [
        {"username": "test_user", "password": "test_password", "disabled": False},
        {"username": "jane_doe", "password": "password", "disabled": True},
    ]

    with test_session() as db_session:
        for user in users_to_add:
            username = user.get("username")
            password = user.get("password")
            disabled = user.get("disabled")

            password = argon2.hash(password)
            new_user = User(
                username=username, hashed_password=password, disabled=disabled
            )
            db_session.add(new_user)
        proceeding = Proceeding(
            proceeding_id=ProceedingId.TEST1,
            proceeding_name="Inquest into death",
            proceeding_description="Inquest into death",
        )
        db_session.add(proceeding)
        db_session.commit()
        application_proceedings_to_add = [
            ApplicationProceeding(proceeding_id=ProceedingId.TEST1)
        ]

        new_public_body = PublicBody(
            public_body_id=PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
            public_body_description="Department for Transport",
        )
        db_session.add(new_public_body)
        db_session.commit()
        application_public_bodies = [
            ApplicationPublicBody(public_body_id=PublicBodyId.DEPARTMENT_FOR_TRANSPORT)
        ]
        home_address = Address(
            address_line_1="1 Example Lane",
            town_or_city="London",
            postcode="SW1A 1AA",
        )
        db_session.add(home_address)
        db_session.commit()
        db_session.refresh(home_address)
        new_client = Client(
            client_first_name="Test",
            client_last_name="Surname",
            date_of_birth="01-02-2003",
            correspondence_address_source="USE_CLIENT_HOME_ADDRESS",
            correspondence_address_id=None,
            home_address_id=home_address.address_id,
        )
        db_session.add(new_client)
        db_session.commit()
        db_session.refresh(new_client)

        new_deceased = Deceased(
            client_id=new_client.client_id,
            deceased_first_name="Test",
            deceased_last_name="Surname",
            deceased_date_of_birth="01-02-1993",
            deceased_date_of_death="01-01-2026",
            coroners_reference="COR-2025-001",
            further_information="Further details to be confirmed",
            client_relationship_to_deceased="sibling",
        )

        db_session.add(new_deceased)
        db_session.commit()
        db_session.refresh(new_deceased)

        new_provider = Provider(
            firm_code="0A123B", office_id="0U651L", email_address="test@example.com"
        )
        db_session.add(new_provider)
        db_session.commit()
        db_session.refresh(new_provider)

        new_application = Application(
            proceedings=application_proceedings_to_add,
            client_id=new_client.client_id,
            deceased_id=new_deceased.deceased_id,
            public_bodies=application_public_bodies,
            provider_id=new_provider.provider_id,
        )

        db_session.add(new_application)
        db_session.commit()
        db_session.refresh(new_application)

        yield db_session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    mock_pdf_generation_port = MagicMock()
    mock_gov_notify_port = MagicMock()

    mock_gov_notify_port.send_application_submit_confirmation_email.return_value = None
    mock_gov_notify_port.send_application_refused_decision_email.return_value = None
    mock_gov_notify_port.send_application_granted_decision_email.return_value = None
    mock_gov_notify_port.send_claim_submit_confirmation_email.return_value = None
    mock_gov_notify_port.send_precompiled_letter.return_value = None

    def get_session_override():
        return session

    def get_provider_details_port_override():
        mock_port = MagicMock()
        mock_port.get_firm_name.return_value = "Test Firm Name"
        mock_port.get_office_address.return_value = Address(
            address_line_1="Test Office Street",
            town_or_city="Test City",
            postcode="TE1 1ST",
        )
        return mock_port

    def get_gov_notify_port_override():
        return mock_gov_notify_port

    def get_pdf_generation_port_override():
        return mock_pdf_generation_port

    def get_sds_port_override():
        mock_sds = MagicMock()
        mock_sds.virus_check_coroners_letter.return_value = True
        mock_sds.save_coroners_letter.return_value = SDSUploadCoronersLetterResponse(
            sds_file_name="test-file_abc123.pdf",
            status="SUCCESS",
        )
        mock_sds.retrieve_coroners_letter.return_value = iter([b"file bytes"])
        return mock_sds

    def get_entra_auth_port_bypass():
        mock_auth = MagicMock()
        mock_auth.verify_token.return_value = None
        return mock_auth

    api.dependency_overrides[get_session] = get_session_override
    api.dependency_overrides[get_provider_details_port] = (
        get_provider_details_port_override
    )
    api.dependency_overrides[get_gov_notify_port] = get_gov_notify_port_override
    api.dependency_overrides[get_pdf_generation_port] = get_pdf_generation_port_override
    api.dependency_overrides[get_sds_port] = get_sds_port_override
    api.dependency_overrides[get_entra_auth_port] = get_entra_auth_port_bypass

    client = TestClient(api, raise_server_exceptions=False)
    yield client
    api.dependency_overrides.clear()


@pytest.fixture(name="entra_auth_client")
def entra_auth_client_fixture(session: Session):
    from fastapi import HTTPException, status

    def get_session_override():
        return session

    def get_provider_details_port_override():
        mock_port = MagicMock()
        mock_port.get_firm_name.return_value = "Test Firm Name"
        mock_port.get_office_address.return_value = Address(
            address_line_1="Test Office Street",
            town_or_city="Test City",
            postcode="TE1 1ST",
        )
        return mock_port

    def get_gov_notify_port_override():
        return MagicMock()

    def get_pdf_generation_port_override():
        mock_port = MagicMock()
        mock_port.generate_pdf.return_value = b"%PDF-1.4\n%Mock PDF content"
        return mock_port

    def get_sds_port_override():
        mock_sds = MagicMock()
        mock_sds.virus_check_coroners_letter.return_value = True
        mock_sds.save_coroners_letter.return_value = SDSUploadCoronersLetterResponse(
            sds_file_name="test-file_abc123.pdf",
            status="SUCCESS",
        )
        mock_sds.retrieve_coroners_letter.return_value = iter([b"file bytes"])
        return mock_sds

    def get_entra_auth_port_override():
        mock_auth = MagicMock()
        token_scopes = {
            "valid-provider-entra-token": {"User.Provider"},
            "valid-caseworker-entra-token": {"User.Caseworker"},
            # Backward compatible alias for existing tests that used one generic token.
            "valid-entra-token": {"User.Provider"},
        }

        def verify_token(token: str, required_scopes: set[str] | None = None) -> None:
            if token == "invalid-token":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if token not in token_scopes:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if required_scopes and required_scopes.isdisjoint(token_scopes[token]):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        mock_auth.verify_token.side_effect = verify_token
        return mock_auth

    api.dependency_overrides[get_session] = get_session_override
    api.dependency_overrides[get_provider_details_port] = (
        get_provider_details_port_override
    )
    api.dependency_overrides[get_gov_notify_port] = get_gov_notify_port_override
    api.dependency_overrides[get_pdf_generation_port] = get_pdf_generation_port_override
    api.dependency_overrides[get_sds_port] = get_sds_port_override
    api.dependency_overrides[get_entra_auth_port] = get_entra_auth_port_override

    yield TestClient(api, raise_server_exceptions=False)
    api.dependency_overrides.clear()


@pytest.fixture
def auth_token(client):
    return "test-token"


@pytest.fixture
def auth_token_disabled_user(client):
    return "disabled-user-test-token"


@pytest.fixture
def mock_gov_notify(client):
    """Return the shared mock Gov Notify port for E2E tests."""
    return api.dependency_overrides[get_gov_notify_port]()


@pytest.fixture
def mock_pdf_generation_port(client):
    """Return the shared mock PDF generation port for E2E tests."""
    return api.dependency_overrides[get_pdf_generation_port]()
