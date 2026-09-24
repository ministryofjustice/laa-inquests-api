import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlmodel import Session, SQLModel, StaticPool, create_engine

from app.models.claim.enums import ClaimDecisionStatus, ClaimStatus, ClaimType
from app.models.claim.index import Claim, ClaimDecision
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

# Naive on purpose: history_event.timestamp and claim.submission_date are stored
# as timezone-naive DateTime columns in Postgres.
BASE_TIME = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)  # noqa: DTZ001


def _make_session() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _make_claim(
    application_id: int,
    claim_reference: str,
    claim_type: ClaimType,
    submission_date: datetime = BASE_TIME,
) -> Claim:
    return Claim(
        application_id=application_id,
        claim_reference=claim_reference,
        claim_type_id=claim_type,
        status_id=ClaimStatus.SUBMITTED,
        submission_date=submission_date,
    )


def _make_decision(
    claim_id: int, decision: ClaimDecisionStatus, created_at: datetime
) -> ClaimDecision:
    return ClaimDecision(claim_id=claim_id, decision=decision, created_at=created_at)


def _make_event(
    application_id: int,
    event_reference: HistoryEventReference,
    event_data: dict,
    timestamp: datetime = BASE_TIME,
) -> HistoryEvent:
    return HistoryEvent(
        event_reference=event_reference,
        actor="actor",
        actor_type=ActorType.PROVIDER,
        application_id=application_id,
        event_data=event_data,
        timestamp=timestamp,
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
    claim = _make_claim(2, "INQC-0020-0020", ClaimType.FINAL_BILL)
    session.add(claim)
    session.flush()
    session.add(
        _make_decision(claim.claim_id, ClaimDecisionStatus.PAY_IN_FULL, BASE_TIME)
    )
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


def test_backfill_resolves_multiple_same_type_claims_by_nearest_timestamp():
    session = _make_session()
    session.add(
        _make_claim(
            4,
            "INQC-0040-0001",
            ClaimType.PAYMENT_ON_ACCOUNT,
            submission_date=BASE_TIME,
        )
    )
    session.add(
        _make_claim(
            4,
            "INQC-0040-0002",
            ClaimType.PAYMENT_ON_ACCOUNT,
            submission_date=BASE_TIME + timedelta(days=30),
        )
    )
    event = _make_event(
        4,
        HistoryEventReference.CLAIM_SUBMITTED,
        {"claim_type": ClaimType.PAYMENT_ON_ACCOUNT.value},
        timestamp=BASE_TIME + timedelta(minutes=1),
    )
    session.add(event)
    session.commit()

    updated = migration.backfill_history_claim_references(session)
    session.commit()

    session.refresh(event)
    assert updated == 1
    assert event.event_data["claim_reference"] == "INQC-0040-0001"


def test_backfill_skips_ambiguous_multiple_claims_equally_close():
    session = _make_session()
    session.add(
        _make_claim(
            5,
            "INQC-0050-0001",
            ClaimType.PAYMENT_ON_ACCOUNT,
            submission_date=BASE_TIME - timedelta(minutes=1),
        )
    )
    session.add(
        _make_claim(
            5,
            "INQC-0050-0002",
            ClaimType.PAYMENT_ON_ACCOUNT,
            submission_date=BASE_TIME + timedelta(minutes=1),
        )
    )
    event = _make_event(
        5,
        HistoryEventReference.CLAIM_SUBMITTED,
        {"claim_type": ClaimType.PAYMENT_ON_ACCOUNT.value},
        timestamp=BASE_TIME,
    )
    session.add(event)
    session.commit()

    updated = migration.backfill_history_claim_references(session)
    session.commit()

    session.refresh(event)
    assert updated == 0
    assert "claim_reference" not in event.event_data


def test_backfill_updates_every_legacy_submitted_event_for_multiple_historic_claims():
    session = _make_session()
    claims = [
        _make_claim(
            6,
            "INQC-0060-0001",
            ClaimType.PAYMENT_ON_ACCOUNT,
            submission_date=BASE_TIME,
        ),
        _make_claim(
            6,
            "INQC-0060-0002",
            ClaimType.PAYMENT_ON_ACCOUNT,
            submission_date=BASE_TIME + timedelta(days=30),
        ),
        _make_claim(
            6,
            "INQC-0060-0003",
            ClaimType.PAYMENT_ON_ACCOUNT,
            submission_date=BASE_TIME + timedelta(days=60),
        ),
    ]
    session.add_all(claims)
    events = [
        _make_event(
            6,
            HistoryEventReference.CLAIM_SUBMITTED,
            {"claim_type": ClaimType.PAYMENT_ON_ACCOUNT.value},
            timestamp=claim.submission_date + timedelta(seconds=1),
        )
        for claim in claims
    ]
    session.add_all(events)
    session.commit()

    updated = migration.backfill_history_claim_references(session)
    session.commit()

    for event in events:
        session.refresh(event)
    assert updated == 3
    assert [event.event_data["claim_reference"] for event in events] == [
        "INQC-0060-0001",
        "INQC-0060-0002",
        "INQC-0060-0003",
    ]


def test_backfill_updates_every_legacy_assessment_event_for_multiple_historic_claims():
    session = _make_session()
    claims = [
        _make_claim(7, "INQC-0070-0001", ClaimType.FINAL_BILL),
        _make_claim(7, "INQC-0070-0002", ClaimType.FINAL_BILL),
    ]
    session.add_all(claims)
    session.flush()
    decisions = [
        _make_decision(claims[0].claim_id, ClaimDecisionStatus.PAY_IN_FULL, BASE_TIME),
        _make_decision(
            claims[1].claim_id,
            ClaimDecisionStatus.REJECT,
            BASE_TIME + timedelta(days=10),
        ),
    ]
    session.add_all(decisions)
    events = [
        _make_event(
            7,
            HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
            {
                "claim_type": ClaimType.FINAL_BILL.value,
                "claim_decision": ClaimStatus.PAY_IN_FULL.value,
            },
            timestamp=BASE_TIME,
        ),
        _make_event(
            7,
            HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
            {
                "claim_type": ClaimType.FINAL_BILL.value,
                "claim_decision": ClaimStatus.REJECTED.value,
            },
            timestamp=BASE_TIME + timedelta(days=10),
        ),
    ]
    session.add_all(events)
    session.commit()

    updated = migration.backfill_history_claim_references(session)
    session.commit()

    for event in events:
        session.refresh(event)
    assert updated == 2
    assert events[0].event_data["claim_reference"] == "INQC-0070-0001"
    assert events[1].event_data["claim_reference"] == "INQC-0070-0002"
