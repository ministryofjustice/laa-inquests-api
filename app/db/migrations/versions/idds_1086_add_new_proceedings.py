"""IDDS-1086 add new proceeding ids IQ011-IQ042 to proceedingid enum

Revision ID: idds_1086_add_new_proceedings
Revises: idds_730_ogd_costs_report
Create Date: 2026-11-03 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "idds_1086_add_new_proceedings"
down_revision: str | Sequence[str] | None = "idds_730_ogd_costs_report"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_VALUES = [
    "IQPC",
    "IQPO",
    "IQMT",
    "IQMH",
    "IQMC",
    "IQCC",
    "IQHO",
    "IQCA",
    "IQDV",
    "IQED",
    "IQTR",
    "IQOT",
]

NEW_VALUES = [f"IQ{n:03d}" for n in range(11, 43)]


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for value in NEW_VALUES:
            op.execute(f"ALTER TYPE proceedingid ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # PostgreSQL cannot DROP enum values, so recreate the type with old values.
    # Data using the new values is moved back by the downgrade of
    # idds_1086_replace_proceedings, which runs before this.
    op.execute(
        "ALTER TABLE application_proceeding "
        "DROP CONSTRAINT application_proceeding_proceeding_id_fkey"
    )

    values_sql = ", ".join(f"'{v}'" for v in OLD_VALUES)
    op.execute("ALTER TYPE proceedingid RENAME TO proceedingid_old")
    op.execute(f"CREATE TYPE proceedingid AS ENUM ({values_sql})")

    for table in ("proceeding", "application_proceeding"):
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN proceeding_id "
            "TYPE proceedingid USING proceeding_id::text::proceedingid"
        )

    op.execute("DROP TYPE proceedingid_old")

    op.execute(
        "ALTER TABLE application_proceeding "
        "ADD CONSTRAINT application_proceeding_proceeding_id_fkey "
        "FOREIGN KEY (proceeding_id) REFERENCES proceeding(proceeding_id)"
    )
