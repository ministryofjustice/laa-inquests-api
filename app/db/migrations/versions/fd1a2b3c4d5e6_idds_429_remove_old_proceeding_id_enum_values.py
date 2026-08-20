"""IDDS-429 remove old proceeding_id enum values and migrate existing data

Revision ID: f1a2b3c4d5e6
Revises: fc72a3f74810
Create Date: 2026-07-28 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "fc72a3f74810"
branch_labels: str | None = None
depends_on: str | None = None

# Old proceeding IDs being retired → new proceeding ID they map to.
OLD_TO_NEW = {
    "PC049": "IQOT",
    "MN035": "IQMT",
    "MN036": "IQPC",
    "MH028": "IQMH",
    "MH030": "IQMH",
    "IQ001": "IQPO",
    "IQ002": "IQOT",
    "IQ003": "IQOT",
    "IQ004": "IQOT",
    "IQ010": "IQOT",
    "TEST1": "IQOT",
}

NEW_VALUES = [
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


def upgrade() -> None:
    # 1. Migrate application_proceeding rows that reference old proceedings.
    #    Point them at the corresponding *new* proceeding row instead.
    #    New enum values were already added by fc72a3f74810.
    for old_val, new_val in OLD_TO_NEW.items():
        # Make sure the target proceeding row exists (seed may not have run yet).
        op.execute(
            sa.text(
                """
                INSERT INTO proceeding (proceeding_id)
                VALUES (CAST(:new_val AS proceedingid))
                ON CONFLICT (proceeding_id) DO NOTHING
                """
            ).bindparams(new_val=new_val)
        )

        # Re-point application_proceeding rows
        op.execute(
            sa.text(
                """
                UPDATE application_proceeding
                SET proceeding_id = CAST(:new_val AS proceedingid)
                WHERE proceeding_id = CAST(:old_val AS proceedingid)
                """
            ).bindparams(old_val=old_val, new_val=new_val)
        )

    # 2. Delete the old proceeding reference-data rows
    for old_val in OLD_TO_NEW:
        op.execute(
            sa.text(
                """
                DELETE FROM proceeding
                WHERE proceeding_id = CAST(:old_val AS proceedingid)
                """
            ).bindparams(old_val=old_val)
        )

    # 3. Recreate the enum type with only new values.
    #    PostgreSQL cannot DROP values from an enum, so we:
    #      a) Drop FK constraint (both columns must use the same type)
    #      b) Create a replacement type
    #      c) Alter every column that uses the old type
    #      d) Drop the old type and rename the new one
    #      e) Re-add the FK constraint
    op.execute(
        "ALTER TABLE application_proceeding "
        "DROP CONSTRAINT application_proceeding_proceeding_id_fkey"
    )

    new_enum = "proceedingid_new"
    values_sql = ", ".join(f"'{v}'" for v in NEW_VALUES)
    op.execute(f"CREATE TYPE {new_enum} AS ENUM ({values_sql})")

    for table, column in [
        ("proceeding", "proceeding_id"),
        ("application_proceeding", "proceeding_id"),
    ]:
        op.execute(
            f"""
            ALTER TABLE {table}
            ALTER COLUMN {column}
            TYPE {new_enum}
            USING {column}::text::{new_enum}
            """
        )

    op.execute("DROP TYPE proceedingid")
    op.execute(f"ALTER TYPE {new_enum} RENAME TO proceedingid")

    op.execute(
        "ALTER TABLE application_proceeding "
        "ADD CONSTRAINT application_proceeding_proceeding_id_fkey "
        "FOREIGN KEY (proceeding_id) REFERENCES proceeding(proceeding_id)"
    )


def downgrade() -> None:
    # Restore old enum values (data migration back is not attempted)
    old_values = list(OLD_TO_NEW.keys())
    all_values = NEW_VALUES + old_values
    values_sql = ", ".join(f"'{v}'" for v in all_values)

    op.execute(
        "ALTER TABLE application_proceeding "
        "DROP CONSTRAINT application_proceeding_proceeding_id_fkey"
    )

    op.execute("ALTER TYPE proceedingid RENAME TO proceedingid_old")
    op.execute(f"CREATE TYPE proceedingid AS ENUM ({values_sql})")

    for table, column in [
        ("proceeding", "proceeding_id"),
        ("application_proceeding", "proceeding_id"),
    ]:
        op.execute(
            f"""
            ALTER TABLE {table}
            ALTER COLUMN {column}
            TYPE proceedingid
            USING {column}::text::proceedingid
            """
        )

    op.execute("DROP TYPE proceedingid_old")

    op.execute(
        "ALTER TABLE application_proceeding "
        "ADD CONSTRAINT application_proceeding_proceeding_id_fkey "
        "FOREIGN KEY (proceeding_id) REFERENCES proceeding(proceeding_id)"
    )
