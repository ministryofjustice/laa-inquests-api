"""IDDS-435 remove old public bodies

Revision ID: 46d24adfe893
Revises: 1d98b6648f95
Create Date: 2026-07-30 15:04:39.539661

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "46d24adfe893"
down_revision: Union[str, None] = "1d98b6648f95"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_ENUM_VALUES = (
    "ATTORNEY_GENERAL",
    "CABINET_OFFICE",
    "DEPARTMENT_DEVOLVED_TO_WALES",
    "DEPARTMENT_FOR_BUSINESS_AND_TRADE",
    "DEPARTMENT_FOR_CULTURE_MEDIA_AND_SPORT",
    "DEPARTMENT_FOR_EDUCATION",
    "DEPARTMENT_FOR_ENERGY_SECURITY_AND_NET_ZERO",
    "DEPARTMENT_FOR_ENVIRONMENT_FOOD_AND_RURAL_AFFAIRS",
    "DEPARTMENT_FOR_HOUSING_COMMUNITIES_AND_LOCAL_GOVERNMENT",
    "DEPARTMENT_FOR_SCIENCE_INNOVATION_AND_TECHNOLOGY",
    "DEPARTMENT_FOR_TRANSPORT",
    "DEPARTMENT_FOR_WORK_AND_PENSIONS",
    "DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE",
    "FOREIGN_COMMONWEALTH_AND_DEVELOPMENT_OFFICE",
    "HM_TREASURY",
    "HOME_OFFICE",
    "MINISTRY_OF_DEFENCE",
    "MINISTRY_OF_JUSTICE",
)

_FK = "application_public_body_public_body_id_fkey"


def upgrade() -> None:
    # Repoint any applications referencing the removed body before the FK and enum are changed.
    op.execute(
        "UPDATE application_public_body "
        "SET public_body_id = 'CABINET_OFFICE' "
        "WHERE public_body_id = 'PRIME_MINISTER_OFFICE'"
    )
    op.execute("DELETE FROM public_body WHERE public_body_id = 'PRIME_MINISTER_OFFICE'")

    # PostgreSQL cannot drop enum values; recreate the type without PRIME_MINISTER_OFFICE.
    enum_values_sql = ", ".join(f"'{v}'" for v in _NEW_ENUM_VALUES)
    op.drop_constraint(_FK, "application_public_body", type_="foreignkey")
    op.execute("ALTER TYPE publicbodyid RENAME TO publicbodyid_old")
    op.execute(f"CREATE TYPE publicbodyid AS ENUM ({enum_values_sql})")
    op.execute(
        "ALTER TABLE public_body "
        "ALTER COLUMN public_body_id TYPE publicbodyid "
        "USING public_body_id::text::publicbodyid"
    )
    op.execute(
        "ALTER TABLE application_public_body "
        "ALTER COLUMN public_body_id TYPE publicbodyid "
        "USING public_body_id::text::publicbodyid"
    )
    op.execute("DROP TYPE publicbodyid_old")
    op.create_foreign_key(
        _FK,
        "application_public_body",
        "public_body",
        ["public_body_id"],
        ["public_body_id"],
    )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE publicbodyid ADD VALUE IF NOT EXISTS 'PRIME_MINISTER_OFFICE'"
        )

    op.execute(
        "INSERT INTO public_body (public_body_id, public_body_description) "
        "VALUES ('PRIME_MINISTER_OFFICE', 'Prime Minister''s Office 10 Downing Street') "
        "ON CONFLICT (public_body_id) DO NOTHING"
    )
