"""Shared factories for E2E tests that need DB-persisted records."""

from datetime import UTC, datetime
import uuid

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
from app.models.claim.enums import ClaimStatus, ClaimType
from app.models.claim.index import Claim


def create_provider_in_db(session: Session, **overrides) -> Provider:
    """Persist a provider with optional field overrides."""
    defaults = {
        "firm_code": "TEST01",
        "office_id": "0U651L",
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
        "date_of_birth": "1990-01-01",
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
        "deceased_date_of_birth": "1960-01-01",
        "deceased_date_of_death": "2026-01-01",
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
        "proceeding": proceeding,
        "public_bodies": [],
        "client_id": client.client_id,
        "deceased_id": deceased.deceased_id,
        "provider_id": provider.provider_id,
        "new_laa_reference": f"INQ-{uuid.uuid4().hex[:6].upper()}-{uuid.uuid4().hex[:6].upper()}",
    }

    application = Application(**(app_defaults | overrides))
    session.add(application)
    session.commit()
    session.refresh(application)
    return application


def create_claim_in_db(
    session: Session,
    *,
    laa_reference: int,
    status: ClaimStatus = ClaimStatus.SUBMITTED,
    submission_date: datetime | None = None,
    total_profit_cost_vat_zero: str = "0.00",
    total_profit_cost_net: str = "100.00",
    total_profit_cost_gross: str = "120.00",
    claim_type: ClaimType = ClaimType.FINAL_BILL,
) -> Claim:
    """Persist a claim with optional field overrides."""
    claim = Claim(
        laa_reference=laa_reference,
        claim_type_id=claim_type,
        status_id=status,
        submission_date=submission_date or datetime.now(UTC),
        total_profit_cost_vat_zero=total_profit_cost_vat_zero,
        total_profit_cost_net=total_profit_cost_net,
        total_profit_cost_gross=total_profit_cost_gross,
    )
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return claim
