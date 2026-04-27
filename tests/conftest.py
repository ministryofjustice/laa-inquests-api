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
    applications_to_add = [
        {
            "status": "PENDING",
            "laa_reference": "INQ-000-001",
            "used_delegated_functions": True,
            "application_type": "INITIAL",
            "auto_grant": True,
            "overall_decision": "PENDING",
        },
        {
            "status": "PENDING",
            "laa_reference": "INQ-000-002",
            "used_delegated_functions": True,
            "application_type": "INITIAL",
            "auto_grant": True,
            "overall_decision": "PENDING",
        },
        {
            "status": "PENDING",
            "laa_reference": "INQ-000-003",
            "used_delegated_functions": True,
            "application_type": "INITIAL",
            "auto_grant": True,
            "overall_decision": "PENDING",
        },
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
        for application in applications_to_add:
            status = application.get("status")
            laa_reference = application.get("laa_reference")
            used_delegated_functions = application.get("used_delegated_functions")
            application_type = application.get("application_type")
            auto_grant = application.get("auto_grant")
            overall_decision = application.get("overall_decision")

            new_application = Application(
                status=status,
                laa_reference=laa_reference,
                used_delegated_functions=used_delegated_functions,
                application_type=application_type,
                auto_grant=auto_grant,
                overall_decision=overall_decision,
            )

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
