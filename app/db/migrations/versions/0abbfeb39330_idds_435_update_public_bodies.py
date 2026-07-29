"""IDDS-435 add public body enum values and description updates

Revision ID: 0abbfeb39330
Revises: fc72a3f74810
Create Date: 2026-07-28 14:06:31.916016

"""

from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0abbfeb39330"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
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

PRE_UPGRADE_PUBLIC_BODIES: tuple[tuple[str, str], ...] = (
    ("PRIME_MINISTER_OFFICE", "Prime Minister's Office 10 Downing Street"),
    ("CABINET_OFFICE", "Cabinet Office"),
    ("ATTORNEY_GENERAL", "Attorney General's Office"),
    ("DEPARTMENT_FOR_BUSINESS_AND_TRADE", "Department for Business & Trade"),
    (
        "DEPARTMENT_FOR_CULTURE_MEDIA_AND_SPORT",
        "Department for Culture, Media & Sport",
    ),
    ("DEPARTMENT_FOR_EDUCATION", "Department for Education"),
    (
        "DEPARTMENT_FOR_ENERGY_SECURITY_AND_NET_ZERO",
        "Department for Energy Security & Net Zero",
    ),
    (
        "DEPARTMENT_FOR_ENVIRONMENT_FOOD_AND_RURAL_AFFAIRS",
        "Department for Environment, Food & Rural Affairs",
    ),
    (
        "DEPARTMENT_FOR_SCIENCE_INNOVATION_AND_TECHNOLOGY",
        "Department for Science, Innovation & Technology",
    ),
    ("DEPARTMENT_FOR_TRANSPORT", "Department for Transport"),
    ("DEPARTMENT_FOR_WORK_AND_PENSIONS", "Department for Work & Pensions"),
    (
        "DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE",
        "Department of Health & Social Care",
    ),
)

APPLICATION_PUBLIC_BODY_PUBLIC_BODY_FK = "application_public_body_public_body_id_fkey"

PRE_UPGRADE_ENUM_VALUES: tuple[str, ...] = tuple(
    enum_key for enum_key, _ in PRE_UPGRADE_PUBLIC_BODIES
)

NEW_ENUM_VALUES: tuple[str, ...] = tuple(
    enum_key for enum_key, _ in PUBLIC_BODIES if enum_key not in PRE_UPGRADE_ENUM_VALUES
)


def _sql_quote(value: str) -> str:
    return value.replace("'", "''")


def _sql_string_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{_sql_quote(value)}'" for value in values)


def upgrade() -> None:
    # Add any new enum values.
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


def downgrade() -> None:
    # Remove only enum values introduced by this migration.
    op.drop_constraint(
        APPLICATION_PUBLIC_BODY_PUBLIC_BODY_FK,
        "application_public_body",
        type_="foreignkey",
    )

    pre_upgrade_enum_values_sql = _sql_string_list(PRE_UPGRADE_ENUM_VALUES)
    new_enum_values_sql = _sql_string_list(NEW_ENUM_VALUES)

    # Repoint existing applications using newly-added public bodies.
    op.execute(
        "UPDATE application_public_body "
        "SET public_body_id = 'CABINET_OFFICE' "
        f"WHERE public_body_id IN ({new_enum_values_sql})"
    )
    # Delete newly-added public bodies from lookup table.
    op.execute(
        f"DELETE FROM public_body WHERE public_body_id IN ({new_enum_values_sql})"
    )

    # Create new enum
    op.execute("ALTER TYPE publicbodyid RENAME TO publicbodyid_old")
    op.execute(f"CREATE TYPE publicbodyid AS ENUM ({pre_upgrade_enum_values_sql})")
    # Update public body values
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

    # Restore the original lookup values and descriptions.
    for enum_key, enum_value in PRE_UPGRADE_PUBLIC_BODIES:
        op.execute(
            "INSERT INTO public_body (public_body_id, public_body_description) "
            f"VALUES ('{_sql_quote(enum_key)}', '{_sql_quote(enum_value)}') "
            "ON CONFLICT (public_body_id) DO UPDATE "
            "SET public_body_description = EXCLUDED.public_body_description "
            "WHERE public_body.public_body_description "
            "IS DISTINCT FROM EXCLUDED.public_body_description"
        )

    op.create_foreign_key(
        APPLICATION_PUBLIC_BODY_PUBLIC_BODY_FK,
        "application_public_body",
        "public_body",
        ["public_body_id"],
        ["public_body_id"],
    )

    op.execute("DROP TYPE publicbodyid_old")
