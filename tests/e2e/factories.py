"""Shared factories for E2E tests that need DB-persisted records."""

import uuid
from datetime import UTC, datetime

from sqlmodel import Session, select

from app.models.application.enums import MeritsDecision
from app.models.application.index import (
    Address,
    Application,
    ApplicationProceeding,
    Client,
    Deceased,
    ProceedingId,
    Provider,
)
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimStatus,
    ClaimType,
    POAType,
    ReasonCode,
)
from app.models.claim.index import (
    Claim,
    ClaimDecision,
    ClaimDecisionAmount,
    ClaimEvidence,
    DecisionReason,
)


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


def create_address_in_db(session: Session, **overrides) -> Address:
    """Persist an address and return it as an Address instance."""
    defaults = {
        "address_line_1": "123 Test Street",
        "town_or_city": "Testville",
        "postcode": "TE57 1NG",
    }
    address = Address(**(defaults | overrides))
    session.add(address)
    session.flush()
    session.refresh(address)
    return address


def create_client_in_db(session: Session, **overrides) -> Client:
    """Persist a client with optional field overrides."""
    defaults = {
        "client_first_name": "Test",
        "client_last_name": "Client",
        "date_of_birth": "1990-01-01",
        "correspondence_address_source": "USE_CLIENT_HOME_ADDRESS",
    }
    client = Client(**(defaults | overrides))
    address = create_address_in_db(session)
    client.home_address = address
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
        "proceeding_id": ProceedingId.IQ042,
        "merits_decision": MeritsDecision.SUBMITTED,
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
        "laa_reference": f"INQ-{uuid.uuid4().hex[:3].upper()}-{uuid.uuid4().hex[:3].upper()}",
    }

    application = Application(**(app_defaults | overrides))
    session.add(application)
    session.commit()
    session.refresh(application)
    return application


def _new_claim_reference() -> str:
    return f"INQC-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"


def get_application_id(session: Session, laa_reference: str | int) -> int:
    return session.exec(
        select(Application.application_id).where(
            Application.laa_reference == laa_reference
        )
    ).one()


def create_claim_in_db(
    session: Session,
    *,
    application_id: int,
    status: ClaimStatus = ClaimStatus.SUBMITTED,
    submission_date: datetime | None = None,
    total_profit_cost_vat_zero: str = "0.00",
    total_profit_cost_net: str = "100.00",
    total_profit_cost_gross: str = "120.00",
    claim_type: ClaimType = ClaimType.FINAL_BILL,
    claim_reference: str | None = None,
    poa_type: POAType | None = None,
    **overrides,
) -> Claim:
    """Persist a claim with optional field overrides."""
    fields = {
        "application_id": application_id,
        "claim_reference": claim_reference or _new_claim_reference(),
        "claim_type_id": claim_type,
        "status_id": status,
        "submission_date": submission_date or datetime.now(UTC),
        "total_profit_cost_vat_zero": total_profit_cost_vat_zero,
        "total_profit_cost_net": total_profit_cost_net,
        "total_profit_cost_gross": total_profit_cost_gross,
        "poa_type_id": poa_type,
    }
    claim = Claim(**(fields | overrides))
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return claim


def create_claim_decision_in_db(
    session: Session, claim_id: int, decision: ClaimDecisionStatus, **overrides
) -> ClaimDecision:
    """Persist a decision for this claim with optional field overrides."""
    claim_decision = ClaimDecision(claim_id=claim_id, decision=decision, **overrides)
    session.add(claim_decision)
    session.commit()
    session.refresh(claim_decision)
    return claim_decision


def create_decision_reason_in_db(
    session: Session, claim_decision_id: int, **overrides
) -> DecisionReason:
    """Persist a decision reason with optional field overrides."""
    defaults = {
        "reason_code": ReasonCode.MAX_POA_CLAIMS_EXCEEDED,
        "justification": "Too many payment on account claims",
    }
    reason = DecisionReason(
        claim_decision_id=claim_decision_id, **(defaults | overrides)
    )
    session.add(reason)
    session.commit()
    session.refresh(reason)
    return reason


def create_claim_decision_amount_in_db(
    session: Session, claim_decision_id: int, **amounts
) -> ClaimDecisionAmount:
    """Persist decision amounts; ``**amounts`` are ``ClaimDecisionAmount`` fields."""
    decision_amount = ClaimDecisionAmount(
        claim_decision_id=claim_decision_id, **amounts
    )
    session.add(decision_amount)
    session.commit()
    session.refresh(decision_amount)
    return decision_amount


def create_claim_evidence_in_db(session: Session, **overrides) -> ClaimEvidence:
    """Persist claim evidence with optional field overrides."""
    defaults = {
        "sds_file_name": "claim-evidence_abc123.pdf",
        "file_name": "test-claim-evidence.pdf",
        "office_id": "0U651L",
    }
    claim_evidence = ClaimEvidence(**(defaults | overrides))
    session.add(claim_evidence)
    session.commit()
    session.refresh(claim_evidence)
    return claim_evidence
