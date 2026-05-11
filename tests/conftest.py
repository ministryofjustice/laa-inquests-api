import pytest
from sqlmodel import SQLModel, create_engine, Session, StaticPool
from app import api
from app.db import get_session
from app.db.session import CustomSession
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.auth.security import get_password_hash
from app.models import User
from app.models.application.index import Application
from app.models.application.proceeding import Proceeding

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
    proceedings_to_add = [
        {"proceeding_id": "TEST1", "proceeding_description": "Test proceeding 1"},
        {"proceeding_id": "TEST2", "proceeding_description": "Test proceeding 2"},
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
        for proceeding in proceedings_to_add:
            proceeding_id = proceeding.get("proceeding_id")
            proceeding_description = proceeding.get("proceeding_description")
            proceeding_to_add = Proceeding(
                proceeding_id=proceeding_id,
                proceeding_description=proceeding_description,
            )
            db_session.add(proceeding_to_add)
            new_application = Application()
            db_session.add(new_application)
        db_session.commit()
        yield db_session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    api.dependency_overrides[get_session] = get_session_override

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
