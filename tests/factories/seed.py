"""Data every ``session`` starts with; the literals here are asserted on by many tests."""

from passlib.hash import argon2
from sqlmodel import Session

from app.models import User
from app.models.application.enums import MeritsDecision
from app.models.application.index import (
    Application,
    Proceeding,
    ProceedingId,
    PublicBody,
    PublicBodyId,
)
from tests.factories import builders
from tests.factories.persisted import create_application, create_coroners_letter

SEED_LAA_REFERENCE = "INQ-123-456"
# Firm of the authenticated user in the conftest auth mock.
TEST_USER_FIRM_CODE = "0A123B"

_SEED_USERS = (
    {"username": "test_user", "password": "test_password", "disabled": False},
    {"username": "jane_doe", "password": "password", "disabled": True},
)


def seed_users(session: Session) -> None:
    for user in _SEED_USERS:
        session.add(
            User(
                username=user["username"],
                hashed_password=argon2.hash(user["password"]),
                disabled=user["disabled"],
            )
        )
    session.commit()


def seed_reference_data(session: Session) -> None:
    session.add(
        Proceeding(
            proceeding_id=ProceedingId.IQOT,
            proceeding_name="Other",
            proceeding_description="Other",
        )
    )
    session.add(
        PublicBody(
            public_body_id=PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
            public_body_description="Department for Transport",
        )
    )
    session.add(
        PublicBody(
            public_body_id=PublicBodyId.DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE,
            public_body_description="Department of Health and Social Care",
        )
    )
    session.commit()


def seed_application(session: Session) -> Application:
    return create_application(
        session,
        laa_reference=SEED_LAA_REFERENCE,
        client_overrides={
            "client_first_name": "Test",
            "client_last_name": "Surname",
            "client_last_name_at_birth": None,
            "date_of_birth": "01-02-2003",
            "national_insurance_number": None,
            "has_applied_previously": False,
            "prev_application_reference": None,
            "home_address": builders.build_home_address(
                address_line_1="1 Example Lane",
                address_line_2=None,
                county=None,
            ),
            "correspondence_address": None,
        },
        deceased_overrides={
            "deceased_first_name": "Test",
            "deceased_last_name": "Surname",
            "deceased_date_of_birth": "01-02-1993",
            "deceased_date_of_death": "01-01-2026",
            "coroners_reference": "COR-2025-001",
            "further_information": "Further details to be confirmed",
            "client_relationship_to_deceased": "sibling",
        },
        provider_overrides={
            "firm_code": TEST_USER_FIRM_CODE,
            "email_address": "test@example.com",
        },
        proceeding_overrides={
            "merits_decision": MeritsDecision.GRANTED,
            "certificate_start_date": None,
            "certificate_issue_date": None,
            "substantive_cost_limitation_effective_date": None,
        },
        coroners_letter=create_coroners_letter(session),
    )
