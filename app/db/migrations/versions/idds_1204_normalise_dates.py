"""IDDS-1204 normalise legacy DD-MM-YYYY deceased dates to ISO YYYY-MM-DD

``deceased_date_of_death`` and ``deceased_date_of_birth`` are free-text columns.
Records created before ISO validation was added can hold day-first dates
(e.g. ``01-02-2003``), which makes the OGD costs report fail with
``Invalid isoformat string``. Day-first (UK convention) values are rewritten
to ISO. Values that are already valid ISO dates are left alone.

If any value is neither a valid ISO date nor a valid DD-MM-YYYY date, the
migration raises before changing anything, listing the ``deceased_id`` values
only, so those records can be corrected by hand.

Revision ID: idds_1204_normalise_dates
Revises: idds_1086_replace_proceedings
Create Date: 2026-11-11 12:00:00.000000

"""

from datetime import date, datetime
from typing import Sequence, Union

from alembic import op
from sqlmodel import Session, select

from app.models.application.index import Deceased

# revision identifiers, used by Alembic.
revision: str = "idds_1204_normalise_dates"
down_revision: Union[str, None] = "idds_1086_replace_proceedings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DATE_FIELDS = ("deceased_date_of_death", "deceased_date_of_birth")
_DAY_FIRST_FORMAT = "%d-%m-%Y"


def _to_iso(value: str) -> str | None:
    """Return the ISO form of ``value``, or None if it is not a valid date."""
    try:
        date.fromisoformat(value)
        return value
    except ValueError:
        pass
    try:
        return datetime.strptime(value, _DAY_FIRST_FORMAT).date().isoformat()
    except ValueError:
        return None


def normalise_deceased_dates(session: Session) -> int:
    """Rewrite day-first dates to ISO and return the number of records changed."""
    changes: list[tuple[Deceased, str, str]] = []
    unconvertible_ids: list[int] = []

    for deceased in session.exec(select(Deceased).order_by(Deceased.deceased_id)):
        for field in _DATE_FIELDS:
            value = getattr(deceased, field)
            iso_value = _to_iso(value)
            if iso_value is None:
                unconvertible_ids.append(deceased.deceased_id)
            elif iso_value != value:
                changes.append((deceased, field, iso_value))

    if unconvertible_ids:
        ids = ", ".join(str(i) for i in sorted(set(unconvertible_ids)))
        raise ValueError(
            f"Cannot convert deceased dates to ISO format for deceased_id: {ids}. "
            "Correct these records manually, then re-run the migration."
        )

    for deceased, field, iso_value in changes:
        setattr(deceased, field, iso_value)
        session.add(deceased)
    return len({deceased.deceased_id for deceased, _, _ in changes})


def upgrade() -> None:
    session = Session(bind=op.get_bind())
    normalise_deceased_dates(session)
    session.flush()


def downgrade() -> None:
    # The original format of each converted value is not recorded.
    pass
