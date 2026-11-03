import importlib.util
from itertools import count
from pathlib import Path

from sqlmodel import Session, SQLModel, StaticPool, create_engine, select

from app.models.application.index import (
    Application,
    ApplicationProceeding,
    Client,
    Deceased,
    DuplicateApplicationRecord,
    ProceedingId,
    Provider,
)

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "db"
    / "migrations"
    / "versions"
    / "7cc4f2bbc722_backfill_duplicate_applications.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "backfill_duplicate_applications_migration", _MIGRATION_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


migration = _load_migration()

_laa_reference_counter = count(1)


def _make_session() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _add_application(
    session: Session,
    *,
    first_name: str,
    last_name: str,
    date_of_birth: str,
    date_of_death: str,
    coroners_reference: str,
) -> int:
    client = Client(
        client_first_name="Client",
        client_last_name="Surname",
        date_of_birth="2000-01-01",
        correspondence_address_source="USE_CLIENT_HOME_ADDRESS",
    )
    provider = Provider(
        firm_code="0A123B", office_id="0U651L", email_address="test@example.com"
    )
    session.add_all([client, provider])
    session.flush()

    deceased = Deceased(
        client_id=client.client_id,
        deceased_first_name=first_name,
        deceased_last_name=last_name,
        deceased_date_of_birth=date_of_birth,
        deceased_date_of_death=date_of_death,
        coroners_reference=coroners_reference,
        further_information=None,
        client_relationship_to_deceased="sibling",
    )
    session.add(deceased)
    session.flush()

    laa_reference_number = next(_laa_reference_counter)
    application = Application(
        client_id=client.client_id,
        deceased_id=deceased.deceased_id,
        provider_id=provider.provider_id,
        laa_reference=f"INQ-{laa_reference_number:03d}-{laa_reference_number:03d}",
        proceeding=ApplicationProceeding(proceeding_id=ProceedingId.IQOT),
    )
    session.add(application)
    session.commit()
    return application.application_id


def _add_matching_applications(session: Session) -> tuple[int, int]:
    """Two applications sharing name and date of birth, which meets the match threshold."""
    first = _add_application(
        session,
        first_name="Jane",
        last_name="Doe",
        date_of_birth="1950-01-01",
        date_of_death="2026-01-01",
        coroners_reference="COR-001",
    )
    second = _add_application(
        session,
        first_name="Jane",
        last_name="Doe",
        date_of_birth="1950-01-01",
        date_of_death="2026-02-02",
        coroners_reference="COR-002",
    )
    return first, second


def _all_pairs(session: Session) -> list[tuple[int, int]]:
    return sorted(
        session.exec(
            select(
                DuplicateApplicationRecord.application_id,
                DuplicateApplicationRecord.duplicate_application_id,
            )
        ).all()
    )


def test_backfill_creates_records_in_both_directions_for_matching_applications():
    session = _make_session()
    first, second = _add_matching_applications(session)

    migration.backfill_duplicate_applications(session)
    session.commit()

    assert _all_pairs(session) == sorted([(first, second), (second, first)])


def test_backfill_does_not_repeat_pairs_that_already_exist():
    session = _make_session()
    first, second = _add_matching_applications(session)
    session.add(
        DuplicateApplicationRecord(
            application_id=first, duplicate_application_id=second
        )
    )
    session.commit()

    migration.backfill_duplicate_applications(session)
    session.commit()

    assert _all_pairs(session) == sorted([(first, second), (second, first)])


def test_backfill_is_idempotent_when_run_twice():
    session = _make_session()
    _add_matching_applications(session)

    migration.backfill_duplicate_applications(session)
    session.commit()
    pairs_after_first_run = _all_pairs(session)

    migration.backfill_duplicate_applications(session)
    session.commit()

    assert _all_pairs(session) == pairs_after_first_run


def test_backfill_creates_no_records_when_fewer_than_two_fields_match():
    session = _make_session()
    _add_application(
        session,
        first_name="Jane",
        last_name="Doe",
        date_of_birth="1950-01-01",
        date_of_death="2026-01-01",
        coroners_reference="COR-001",
    )
    _add_application(
        session,
        first_name="John",
        last_name="Smith",
        date_of_birth="1950-01-01",
        date_of_death="2026-02-02",
        coroners_reference="COR-002",
    )

    migration.backfill_duplicate_applications(session)
    session.commit()

    assert _all_pairs(session) == []
