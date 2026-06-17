import pytest
from unittest.mock import MagicMock
from sqlmodel import SQLModel, create_engine, Session, StaticPool
from app import api
from app.db import get_session
from app.db.session import CustomSession
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from app.auth.security import get_password_hash
from app.routers.applications import get_provider_details_port
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

            password = get_password_hash(password)
            new_user = User(
                username=username, hashed_password=password, disabled=disabled
            )
            db_session.add(new_user)
        proceeding = Proceeding(proceeding_id=ProceedingId.TEST1)
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
            firm_code="0A123B", office_id="001", email="test@example.com"
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
    def get_session_override():
        return session

    def get_provider_details_port_override():
        mock_port = MagicMock()
        mock_port.get_firm_name.return_value = "Test Firm Name"
        return mock_port

    api.dependency_overrides[get_session] = get_session_override
    api.dependency_overrides[get_provider_details_port] = (
        get_provider_details_port_override
    )

    client = TestClient(api)
    yield client
    api.dependency_overrides.clear()


@pytest.fixture
def auth_token(client):
    # Send POST request with x-www-form-urlencoded data
    response = client.post(
        "/token",
        data={"username": "test_user", "password": "test_password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    return token_data["access_token"]


@pytest.fixture
def auth_token_disabled_user(client):
    # Send POST request with x-www-form-urlencoded data
    response = client.post(
        "/token",
        data={"username": "jane_doe", "password": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    return token_data["access_token"]
