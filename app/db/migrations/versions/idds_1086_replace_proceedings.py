"""IDDS-1086 replace proceedings with IQ011-IQ042 and remove old enum values

Revision ID: idds_1086_replace_proceedings
Revises: idds_1086_add_new_proceedings
Create Date: 2026-11-03 12:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "idds_1086_replace_proceedings"
down_revision: str | Sequence[str] | None = "idds_1086_add_new_proceedings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_PROCEEDINGS = {
    "IQ011": "An individual has died in police custody",
    "IQ012": "An individual has died during police pursuit",
    "IQ013": "An individual has died following a police shooting",
    "IQ014": "An individual has died in prison",
    "IQ015": "An individual has died following release from custody / prison",
    "IQ016": "An individual has died in a young offender’s institution",
    "IQ017": "An individual has died in detention under the Mental Health Act 1983",
    "IQ018": "An individual has died during or following medical care or treatment",
    "IQ019": "An individual has died following failure, or alleged failure, to provide medical treatment",
    "IQ020": "An individual has died while receiving mental health care in the community",
    "IQ021": "An individual has died while receiving care in the community (non-mental health)",
    "IQ022": "An individual has died while in supported living",
    "IQ023": "An individual has died following failure, or alleged failure, to provide care services",
    "IQ024": "An individual has died from alleged safeguarding failures",
    "IQ025": "A child has died that was subject to a care or interim care order",
    "IQ026": "A child has died following from failure, or alleged failure, to take a child into care",
    "IQ027": "A child has died from alleged deliberate abuse of a child in care",
    "IQ028": "A child has died by alleged suicide",
    "IQ029": "A child has died that was subject to safeguarding concerns",
    "IQ030": "A child has died that was referred to social services",
    "IQ031": "A child has died with Special Educational Needs and Disabilities (SEND)",
    "IQ032": "An individual has died in an educational setting",
    "IQ033": "An individual has died from failures, or alleged failures, of an educational institution",
    "IQ034": "An individual has died in immigration detention",
    "IQ035": "An individual has died that was seeking asylum in the country",
    "IQ036": "An individual has died from alleged issues with the condition of housing",
    "IQ037": "An individual has died in connection with their lack of housing",
    "IQ038": "An individual has died following the termination of disability benefits",
    "IQ039": "An individual has died following alleged mental health issues while in the military",
    "IQ040": "An individual has died from a road traffic collision",
    "IQ041": "An individual has died in an incident involving public transport",
    "IQ042": "A family member has died (Other)",
}

OLD_PROCEEDINGS = {
    "IQPC": "Death in police custody",
    "IQPO": "Death in prison",
    "IQMT": "Death during medical treatment",
    "IQMH": "Death in mental health detention",
    "IQMC": "Death relating to mental health care in the community",
    "IQCC": "Death relating to other care in the community",
    "IQHO": "Death relating to issues with condition/safety of housing",
    "IQCA": "Death relating to a child’s care arrangements",
    "IQDV": "Death relating to failure to prevent domestic violence",
    "IQED": "Death relating to issues in an educational setting",
    "IQTR": "Death relating to issues relating to transport",
    "IQOT": "Other",
}

OLD_TO_NEW = {
    "IQPC": "IQ011",
    "IQPO": "IQ014",
    "IQMT": "IQ018",
    "IQMH": "IQ017",
    "IQMC": "IQ020",
    "IQCC": "IQ021",
    "IQHO": "IQ036",
    "IQCA": "IQ025",
    "IQDV": "IQ042",
    "IQED": "IQ032",
    "IQTR": "IQ041",
    "IQOT": "IQ042",
}

# Used on downgrade; new codes without a direct old equivalent fall back to IQOT.
NEW_TO_OLD = {
    new: old for old, new in OLD_TO_NEW.items() if old not in ("IQDV", "IQOT")
}
DOWNGRADE_FALLBACK = "IQOT"


def _upsert_proceedings(proceedings: dict[str, str]) -> None:
    for proceeding_id, name in proceedings.items():
        op.execute(
            sa.text(
                """
                INSERT INTO proceeding (
                    proceeding_id,
                    proceeding_name,
                    proceeding_description,
                    category_of_law,
                    certificate_type,
                    level_of_service,
                    matter_type,
                    scope_limitation_heading,
                    scope_description,
                    substantive_cost_limitation
                )
                VALUES (
                    CAST(:proceeding_id AS proceedingid),
                    :name,
                    :name,
                    'INQUESTS',
                    'SUBSTANTIVE',
                    'FULL_REPRESENTATION',
                    'INQUESTS',
                    'FINAL_HEARING',
                    'This is the scope description',
                    10000
                )
                ON CONFLICT (proceeding_id) DO UPDATE SET
                    proceeding_name = EXCLUDED.proceeding_name,
                    proceeding_description = EXCLUDED.proceeding_description
                """
            ).bindparams(proceeding_id=proceeding_id, name=name)
        )


def _repoint_application_proceedings(from_id: str, to_id: str) -> None:
    op.execute(
        sa.text(
            """
            UPDATE application_proceeding
            SET proceeding_id = CAST(:to_id AS proceedingid)
            WHERE proceeding_id = CAST(:from_id AS proceedingid)
            """
        ).bindparams(from_id=from_id, to_id=to_id)
    )


def _delete_proceedings(proceeding_ids) -> None:
    for proceeding_id in proceeding_ids:
        op.execute(
            sa.text(
                "DELETE FROM proceeding "
                "WHERE proceeding_id = CAST(:proceeding_id AS proceedingid)"
            ).bindparams(proceeding_id=proceeding_id)
        )


def upgrade() -> None:
    # New enum values were added (and committed) by idds_1086_add_new_proceedings.
    _upsert_proceedings(NEW_PROCEEDINGS)

    for old_id, new_id in OLD_TO_NEW.items():
        _repoint_application_proceedings(old_id, new_id)

    _delete_proceedings(OLD_PROCEEDINGS)

    # PostgreSQL cannot DROP enum values, so recreate the type with new values only.
    op.execute(
        "ALTER TABLE application_proceeding "
        "DROP CONSTRAINT application_proceeding_proceeding_id_fkey"
    )

    values_sql = ", ".join(f"'{v}'" for v in NEW_PROCEEDINGS)
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


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for value in OLD_PROCEEDINGS:
            op.execute(f"ALTER TYPE proceedingid ADD VALUE IF NOT EXISTS '{value}'")

    _upsert_proceedings(OLD_PROCEEDINGS)

    for new_id in NEW_PROCEEDINGS:
        _repoint_application_proceedings(
            new_id, NEW_TO_OLD.get(new_id, DOWNGRADE_FALLBACK)
        )

    _delete_proceedings(NEW_PROCEEDINGS)
