import importlib.util
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, StaticPool, create_engine

from app.models.application.index import Deceased

_MIGRATION_PATH = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "db"
    / "migrations"
    / "versions"
    / "idds_1204_normalise_dates.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "idds_1204_normalise_dates", _MIGRATION_PATH
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


def _add_deceased(
    session: Session,
    date_of_death: str = "2020-01-04",
    date_of_birth: str = "1990-07-06",
) -> Deceased:
    deceased = Deceased(
        client_id=1,
        deceased_first_name="Tom",
        deceased_last_name="Jaylor",
        deceased_date_of_birth=date_of_birth,
        deceased_date_of_death=date_of_death,
        coroners_reference="coroner",
        further_information=None,
        client_relationship_to_deceased="Father",
    )
    session.add(deceased)
    session.commit()
    return deceased


def test_converts_day_first_date_of_death_to_iso():
    session = _make_session()
    deceased = _add_deceased(session, date_of_death="01-02-2003")

    updated = migration.normalise_deceased_dates(session)
    session.commit()

    session.refresh(deceased)
    assert updated == 1
    assert deceased.deceased_date_of_death == "2003-02-01"


def test_converts_day_first_date_of_birth_to_iso():
    session = _make_session()
    deceased = _add_deceased(session, date_of_birth="15-06-1980")

    migration.normalise_deceased_dates(session)
    session.commit()

    session.refresh(deceased)
    assert deceased.deceased_date_of_birth == "1980-06-15"
    assert deceased.deceased_date_of_death == "2020-01-04"


def test_converts_both_dates_on_the_same_record():
    session = _make_session()
    deceased = _add_deceased(
        session, date_of_death="25-12-2019", date_of_birth="15-06-1980"
    )

    updated = migration.normalise_deceased_dates(session)
    session.commit()

    session.refresh(deceased)
    assert updated == 1
    assert deceased.deceased_date_of_death == "2019-12-25"
    assert deceased.deceased_date_of_birth == "1980-06-15"


def test_leaves_iso_dates_unchanged():
    session = _make_session()
    deceased = _add_deceased(session)

    updated = migration.normalise_deceased_dates(session)
    session.commit()

    session.refresh(deceased)
    assert updated == 0
    assert deceased.deceased_date_of_death == "2020-01-04"
    assert deceased.deceased_date_of_birth == "1990-07-06"


def test_running_twice_changes_nothing_more():
    session = _make_session()
    deceased = _add_deceased(session, date_of_death="01-02-2003")
    migration.normalise_deceased_dates(session)
    session.commit()

    updated = migration.normalise_deceased_dates(session)
    session.commit()

    session.refresh(deceased)
    assert updated == 0
    assert deceased.deceased_date_of_death == "2003-02-01"


@pytest.mark.parametrize("bad_value", ["not a date", "31-02-2003", "2026-02-30"])
def test_raises_for_values_that_cannot_be_converted_without_changing_any_row(
    bad_value,
):
    session = _make_session()
    convertible = _add_deceased(session, date_of_death="01-02-2003")
    unconvertible = _add_deceased(session, date_of_death=bad_value)

    with pytest.raises(ValueError) as exc_info:
        migration.normalise_deceased_dates(session)

    message = str(exc_info.value)
    assert str(unconvertible.deceased_id) in message
    assert bad_value not in message
    session.rollback()
    session.refresh(convertible)
    assert convertible.deceased_date_of_death == "01-02-2003"


def test_downgrade_does_nothing():
    assert migration.downgrade() is None
