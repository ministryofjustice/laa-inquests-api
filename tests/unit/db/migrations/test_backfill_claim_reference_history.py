import importlib.util
from pathlib import Path

from sqlmodel import Session, SQLModel, StaticPool, create_engine

from app.models.claim.enums import ClaimStatus, ClaimType
from app.models.claim.index import Claim
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "db"
    / "migrations"
    / "versions"
    / "idds_867_backfill_hist_ref.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "idds_867_backfill_hist_ref", _MIGRATION_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


migration = _load_migration()


def _make_session() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _make_claim(
    application_id: int, claim_reference: str, claim_type: ClaimType
) -> Claim:
    return Claim(
        application_id=application_id,
        claim_reference=claim_reference,
        claim_type_id=claim_type,
        status_id=ClaimStatus.SUBMITTED,
    )


def _make_event(
    application_id: int,
    event_reference: HistoryEventReference,
    event_data: dict,
) -> HistoryEvent:
    return HistoryEvent(
        event_reference=event_reference,
        actor="actor",
        actor_type=ActorType.PROVIDER,
        application_id=application_id,
        event_data=event_data,
    )


def test_backfill_populates_claim_reference_for_submitted_event():
    session = _make_session()
    session.add(_make_claim(1, "INQC-0010-0010", ClaimType.PAYMENT_ON_ACCOUNT))
    event = _make_event(
        1,
        HistoryEventReference.CLAIM_SUBMITTED,
        {"claim_type": ClaimType.PAYMENT_ON_ACCOUNT.value},
    )
    session.add(event)
    session.commit()

    updated = migration.backfill_history_claim_references(session)
    session.commit()

    session.refresh(event)
    assert updated == 1
    assert event.event_data == {
        "claim_type": ClaimType.PAYMENT_ON_ACCOUNT.value,
        "claim_reference": "INQC-0010-0010",
    }


def test_backfill_populates_claim_reference_for_assessment_event():
    session = _make_session()
    session.add(_make_claim(2, "INQC-0020-0020", ClaimType.FINAL_BILL))
    event = _make_event(
        2,
        HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
        {
            "claim_type": ClaimType.FINAL_BILL.value,
            "claim_decision": ClaimStatus.PAY_IN_FULL.value,
        },
    )
    session.add(event)
    session.commit()

    migration.backfill_history_claim_references(session)
    session.commit()

    session.refresh(event)
    assert event.event_data["claim_reference"] == "INQC-0020-0020"


def test_backfill_leaves_existing_claim_reference_untouched():
    session = _make_session()
    session.add(_make_claim(3, "INQC-0030-0030", ClaimType.PAYMENT_ON_ACCOUNT))
    event = _make_event(
        3,
        HistoryEventReference.CLAIM_SUBMITTED,
        {
            "claim_type": ClaimType.PAYMENT_ON_ACCOUNT.value,
            "claim_reference": "INQC-9999-9999",
        },
    )
    session.add(event)
    session.commit()

    updated = migration.backfill_history_claim_references(session)
    session.commit()

    session.refresh(event)
    assert updated == 0
    assert event.event_data["claim_reference"] == "INQC-9999-9999"


def test_backfill_skips_ambiguous_multiple_claims_of_same_type():
    session = _make_session()
    session.add(_make_claim(4, "INQC-0040-0001", ClaimType.PAYMENT_ON_ACCOUNT))
    session.add(_make_claim(4, "INQC-0040-0002", ClaimType.PAYMENT_ON_ACCOUNT))
    event = _make_event(
        4,
        HistoryEventReference.CLAIM_SUBMITTED,
        {"claim_type": ClaimType.PAYMENT_ON_ACCOUNT.value},
    )
    session.add(event)
    session.commit()

    updated = migration.backfill_history_claim_references(session)
    session.commit()

    session.refresh(event)
    assert updated == 0
    assert "claim_reference" not in event.event_data
