from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, StaticPool, create_engine, select

from app import api
from app.auth.rbac import ROLE_PERMISSIONS_MAP
from app.db import get_session
from app.db.session import CustomSession
from app.models.application.index import (
    Application,
    SDSUploadClaimEvidenceResponse,
    SDSUploadCoronersLetterResponse,
)
from app.ports.entra_auth_port import AuthenticatedUser
from app.routers.applications import (
    get_gov_notify_port,
    get_pdf_generation_port,
    get_provider_details_port,
    get_sds_port,
)
from app.routers.dependencies import get_entra_auth_port
from tests.factories.builders import build_office_address
from tests.factories.seed import (
    SEED_LAA_REFERENCE,
    TEST_USER_FIRM_CODE,
    seed_application,
    seed_reference_data,
    seed_users,
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
    with test_session() as db_session:
        seed_users(db_session)
        seed_reference_data(db_session)
        seed_application(db_session)

        yield db_session


@pytest.fixture
def seeded_application(session: Session) -> Application:
    return session.exec(
        select(Application).where(Application.laa_reference == SEED_LAA_REFERENCE)
    ).one()


@pytest.fixture(name="client")
def client_fixture(session: Session):
    mock_pdf_generation_port = MagicMock()
    mock_pdf_generation_port.generate_pdf.return_value = b"%PDF-1.4\n%Mock PDF content"

    mock_gov_notify_port = MagicMock()

    mock_gov_notify_port.send_application_submit_confirmation_email.return_value = None
    mock_gov_notify_port.send_application_refused_decision_email.return_value = None
    mock_gov_notify_port.send_application_granted_decision_email.return_value = None
    mock_gov_notify_port.send_claim_submit_confirmation_email.return_value = None
    mock_gov_notify_port.send_claim_rejected_decision_email.return_value = None
    mock_gov_notify_port.send_claim_final_bill_paid_decision_email.return_value = None
    mock_gov_notify_port.send_precompiled_letter.return_value = None

    def get_session_override():
        return session

    def get_provider_details_port_override():
        mock_port = MagicMock()
        mock_port.get_firm_name.return_value = "Test Firm Name"
        mock_port.get_firms_by_ids.side_effect = lambda firm_ids: [
            {"firmNumber": fid, "firmName": f"Firm {fid}"} for fid in firm_ids
        ]
        mock_port.get_office_address.return_value = build_office_address(
            address_line_1="Test Office Street",
            address_line_2=None,
            town_or_city="Test City",
            county=None,
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
        mock_sds.virus_check_claim_evidence.return_value = True
        mock_sds.save_claim_evidence.return_value = SDSUploadClaimEvidenceResponse(
            sds_file_name="test-claim-evidence_abc123.pdf",
            status="SUCCESS",
        )
        mock_sds.retrieve_coroners_letter.return_value = iter([b"file bytes"])
        mock_sds.retrieve_claim_evidence.return_value = iter([b"file bytes"])
        return mock_sds

    def get_entra_auth_port_override():
        mock_auth = MagicMock()

        # Pass in a Role.value (e.g. Role.PROVIDER_APPLICATION_USER.value) or Provider/Caseworker No Role
        def verify_token(
            role: str, required_scopes: set[str] | None = None
        ) -> AuthenticatedUser:
            app_roles: frozenset
            scopes: frozenset

            if role in ROLE_PERMISSIONS_MAP:
                app_roles = frozenset([role])
                scopes = frozenset(
                    ["User.Provider" if "Provider" in role else "User.Caseworker"]
                )
            elif "No Role" in role:
                app_roles = frozenset()
                scopes = frozenset(
                    ["User.Provider" if "Provider" in role else "User.Caseworker"]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if required_scopes and required_scopes.isdisjoint(scopes):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return AuthenticatedUser(
                firm_code=TEST_USER_FIRM_CODE,
                scopes=scopes,
                name="Test Name",
                app_roles=app_roles,
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

    client = TestClient(api, raise_server_exceptions=False)
    yield client
    api.dependency_overrides.clear()


@pytest.fixture
def mock_gov_notify(client):
    """Return the shared mock Gov Notify port for E2E tests."""
    return api.dependency_overrides[get_gov_notify_port]()


@pytest.fixture
def mock_pdf_generation_port(client):
    """Return the shared mock PDF generation port for E2E tests."""
    return api.dependency_overrides[get_pdf_generation_port]()
