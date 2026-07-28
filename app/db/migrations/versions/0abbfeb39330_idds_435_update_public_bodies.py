"""IDDS-435 update public bodies

Revision ID: 0abbfeb39330
Revises: fc72a3f74810
Create Date: 2026-07-28 14:06:31.916016

"""

from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0abbfeb39330"
down_revision: Union[str, None] = "fc72a3f74810"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PUBLIC_BODIES: tuple[tuple[str, str], ...] = (
    ("ATTORNEY_GENERAL", "Attorney General's Office"),
    ("CABINET_OFFICE", "Cabinet Office"),
    ("DEPARTMENT_DEVOLVED_TO_WALES", "Department Devolved to Wales"),
    ("DEPARTMENT_FOR_BUSINESS_AND_TRADE", "Department for Business and Trade"),
    (
        "DEPARTMENT_FOR_CULTURE_MEDIA_AND_SPORT",
        "Department for Culture, Media and Sport",
    ),
    ("DEPARTMENT_FOR_EDUCATION", "Department for Education"),
    (
        "DEPARTMENT_FOR_ENERGY_SECURITY_AND_NET_ZERO",
        "Department for Energy Security and Net Zero",
    ),
    (
        "DEPARTMENT_FOR_ENVIRONMENT_FOOD_AND_RURAL_AFFAIRS",
        "Department for Environment, Food and Rural Affairs",
    ),
    (
        "DEPARTMENT_FOR_HOUSING_COMMUNITIES_AND_LOCAL_GOVERNMENT",
        "Department for Housing, Communities and Local Government",
    ),
    (
        "DEPARTMENT_FOR_SCIENCE_INNOVATION_AND_TECHNOLOGY",
        "Department for Science, Innovation and Technology",
    ),
    ("DEPARTMENT_FOR_TRANSPORT", "Department for Transport"),
    ("DEPARTMENT_FOR_WORK_AND_PENSIONS", "Department for Work and Pensions"),
    (
        "DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE",
        "Department of Health and Social Care",
    ),
    (
        "FOREIGN_COMMONWEALTH_AND_DEVELOPMENT_OFFICE",
        "Foreign, Commonwealth and Development Office",
    ),
    ("HM_TREASURY", "HM Treasury"),
    ("HOME_OFFICE", "Home Office"),
    ("MINISTRY_OF_DEFENCE", "Ministry of Defence"),
    ("MINISTRY_OF_JUSTICE", "Ministry of Justice"),
)

APPLICATION_PUBLIC_BODY_PUBLIC_BODY_FK = "application_public_body_public_body_id_fkey"


def _sql_quote(value: str) -> str:
    return value.replace("'", "''")


def upgrade() -> None:
    # Add non-existant enum values. With statement to add immediatley
    with op.get_context().autocommit_block():
        for enum_key, _ in PUBLIC_BODIES:
            op.execute(
                "ALTER TYPE publicbodyid ADD VALUE IF NOT EXISTS "
                f"'{_sql_quote(enum_key)}'"
            )

    # Insert new rows into public_body. Update description if new
    for enum_key, enum_value in PUBLIC_BODIES:
        op.execute(
            "INSERT INTO public_body (public_body_id, public_body_description) "
            f"VALUES ('{_sql_quote(enum_key)}', '{_sql_quote(enum_value)}') "
            "ON CONFLICT (public_body_id) DO UPDATE "
            "SET public_body_description = EXCLUDED.public_body_description "
            "WHERE public_body.public_body_description "
            "IS DISTINCT FROM EXCLUDED.public_body_description"
        )

    # Update rows referencing to-be-deleted PRIME_MINISTER_OFFICE enum
    op.execute(
        "UPDATE application_public_body "
        "SET public_body_id = 'CABINET_OFFICE' "
        "WHERE public_body_id = 'PRIME_MINISTER_OFFICE'"
    )

    # We want to remove PRIME_MINISTER_OFFICE.
    # We cannot remove an enum value directly. So the way to do this is create a new enum and swap it
    # However, foreign keys block that, so we need to temporarily drop them
    # This isn't great, but the only way we can really do this with enums as FKs
    op.drop_constraint(
        APPLICATION_PUBLIC_BODY_PUBLIC_BODY_FK,
        "application_public_body",
        type_="foreignkey",
    )

    # Recreate enum type without PRIME_MINISTER_OFFICE.
    op.execute("ALTER TYPE publicbodyid RENAME TO publicbodyid_old")
    op.execute(
        "CREATE TYPE publicbodyid AS ENUM "
        "('ATTORNEY_GENERAL', "
        "'CABINET_OFFICE', "
        "'DEPARTMENT_DEVOLVED_TO_WALES', "
        "'DEPARTMENT_FOR_BUSINESS_AND_TRADE', "
        "'DEPARTMENT_FOR_CULTURE_MEDIA_AND_SPORT', "
        "'DEPARTMENT_FOR_EDUCATION', "
        "'DEPARTMENT_FOR_ENERGY_SECURITY_AND_NET_ZERO', "
        "'DEPARTMENT_FOR_ENVIRONMENT_FOOD_AND_RURAL_AFFAIRS', "
        "'DEPARTMENT_FOR_HOUSING_COMMUNITIES_AND_LOCAL_GOVERNMENT', "
        "'DEPARTMENT_FOR_SCIENCE_INNOVATION_AND_TECHNOLOGY', "
        "'DEPARTMENT_FOR_TRANSPORT', "
        "'DEPARTMENT_FOR_WORK_AND_PENSIONS', "
        "'DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE', "
        "'FOREIGN_COMMONWEALTH_AND_DEVELOPMENT_OFFICE', "
        "'HM_TREASURY', "
        "'HOME_OFFICE', "
        "'MINISTRY_OF_DEFENCE', "
        "'MINISTRY_OF_JUSTICE')"
    )

    # Re-assign enums
    op.execute(
        "ALTER TABLE public_body "
        "ALTER COLUMN public_body_id "
        "TYPE publicbodyid "
        "USING public_body_id::text::publicbodyid"
    )
    op.execute(
        "ALTER TABLE application_public_body "
        "ALTER COLUMN public_body_id "
        "TYPE publicbodyid "
        "USING public_body_id::text::publicbodyid"
    )

    op.create_foreign_key(
        APPLICATION_PUBLIC_BODY_PUBLIC_BODY_FK,
        "application_public_body",
        "public_body",
        ["public_body_id"],
        ["public_body_id"],
    )

    op.execute("DROP TYPE publicbodyid_old")


def downgrade() -> None:
    # PostgreSQL enums do not support value removal downgrade safely.
    pass
