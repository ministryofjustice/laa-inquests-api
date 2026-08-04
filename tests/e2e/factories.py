"""Shared factories for E2E tests that need DB-persisted records."""

from sqlmodel import Session

from app.models.application.enums import MeritsDecision
from app.models.application.index import (
    Application,
    ApplicationProceeding,
    Client,
    Deceased,
    ProceedingId,
    Provider,
)


def create_provider_in_db(session: Session, **overrides) -> Provider:
    """Persist a provider with optional field overrides."""
    defaults = {
        "firm_code": "TEST01",
        "office_id": "001",
        "email_address": "test@example.com",
    }
    provider = Provider(**(defaults | overrides))
    session.add(provider)
    session.flush()
    session.refresh(provider)
    return provider


def create_client_in_db(session: Session, **overrides) -> Client:
    """Persist a client with optional field overrides."""
    defaults = {
        "client_first_name": "Test",
        "client_last_name": "Client",
        "date_of_birth": "01-01-1990",
        "correspondence_address_source": "USE_CLIENT_HOME_ADDRESS",
    }
    client = Client(**(defaults | overrides))
    session.add(client)
    session.flush()
    session.refresh(client)
    return client


def create_deceased_in_db(session: Session, *, client_id: int, **overrides) -> Deceased:
    """Persist a deceased with optional field overrides."""
    defaults = {
        "client_id": client_id,
        "deceased_first_name": "Dec",
        "deceased_last_name": "Eased",
        "deceased_date_of_birth": "01-01-1960",
        "deceased_date_of_death": "01-01-2026",
        "coroners_reference": "COR-TEST-001",
        "further_information": None,
        "client_relationship_to_deceased": "spouse",
    }
    deceased = Deceased(**(defaults | overrides))
    session.add(deceased)
    session.flush()
    session.refresh(deceased)
    return deceased


def create_application_in_db(
    session: Session,
    *,
    provider_overrides: dict | None = None,
    client_overrides: dict | None = None,
    deceased_overrides: dict | None = None,
    proceeding_overrides: dict | None = None,
    **overrides,
) -> Application:
    """Persist a full application with related objects and return it.

    Each nested object can be customised via its ``*_overrides`` dict.
    Top-level ``**overrides`` are applied to the Application itself.
    """
    provider = create_provider_in_db(session, **(provider_overrides or {}))
    client = create_client_in_db(session, **(client_overrides or {}))
    deceased = create_deceased_in_db(
        session, client_id=client.client_id, **(deceased_overrides or {})
    )

    proceeding_defaults = {
        "proceeding_id": ProceedingId.IQOT,
        "merits_decision": MeritsDecision.PENDING,
    }
    proceeding = ApplicationProceeding(
        **(proceeding_defaults | (proceeding_overrides or {}))
    )

    app_defaults: dict = {
        "proceedings": [proceeding],
        "public_bodies": [],
        "client_id": client.client_id,
        "deceased_id": deceased.deceased_id,
        "provider_id": provider.provider_id,
    }

    application = Application(**(app_defaults | overrides))
    session.add(application)
    session.commit()
    session.refresh(application)
    return application
