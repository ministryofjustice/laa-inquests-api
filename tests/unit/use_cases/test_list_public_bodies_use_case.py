from unittest.mock import MagicMock

from app.models.application.index import PublicBody, PublicBodyId
from app.ports.list_public_bodies_port import ListPublicBodiesPort
from app.use_cases.list_public_bodies import ListPublicBodiesUseCase


def test_execute_returns_empty_list_when_no_public_bodies_exist():
    port = MagicMock(spec=ListPublicBodiesPort)
    port.list_public_bodies.return_value = []

    result = ListPublicBodiesUseCase(list_public_bodies_port=port).execute()

    assert result == []


def test_execute_sorts_alphabetically():
    bodies = [
        PublicBody(
            public_body_id=PublicBodyId.HOME_OFFICE,
            public_body_description="Home Office",
        ),
        PublicBody(
            public_body_id=PublicBodyId.DEPARTMENT_DEVOLVED_TO_WALES,
            public_body_description="Department Devolved to Wales",
        ),
        PublicBody(
            public_body_id=PublicBodyId.CABINET_OFFICE,
            public_body_description="Cabinet Office",
        ),
    ]
    port = MagicMock(spec=ListPublicBodiesPort)
    port.list_public_bodies.return_value = bodies

    result = ListPublicBodiesUseCase(list_public_bodies_port=port).execute()

    assert [b.public_body_description for b in result] == [
        "Cabinet Office",
        "Department Devolved to Wales",
        "Home Office",
    ]


def test_execute_sorts_department_for_and_of_entries_as_equivalent():
    # "Department of Health" and "Department for Transport" compare as if both say "Department for ..."
    bodies = [
        PublicBody(
            public_body_id=PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
            public_body_description="Department for Transport",
        ),
        PublicBody(
            public_body_id=PublicBodyId.DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE,
            public_body_description="Department of Health and Social Care",
        ),
        PublicBody(
            public_body_id=PublicBodyId.DEPARTMENT_FOR_EDUCATION,
            public_body_description="Department for Education",
        ),
    ]
    port = MagicMock(spec=ListPublicBodiesPort)
    port.list_public_bodies.return_value = bodies

    result = ListPublicBodiesUseCase(list_public_bodies_port=port).execute()

    assert [b.public_body_description for b in result] == [
        "Department for Education",
        "Department of Health and Social Care",
        "Department for Transport",
    ]
