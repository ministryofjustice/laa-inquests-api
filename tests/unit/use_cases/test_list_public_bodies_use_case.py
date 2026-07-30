from unittest.mock import MagicMock

from app.models.application.index import PublicBody, PublicBodyId
from app.ports.list_public_bodies_port import ListPublicBodiesPort
from app.use_cases.list_public_bodies import ListPublicBodiesUseCase


def _make_body(public_body_id: PublicBodyId, description: str) -> PublicBody:
    return PublicBody(
        public_body_id=public_body_id, public_body_description=description
    )


def test_execute_sorts_department_for_and_of_by_meaningful_word():
    # "Department of Health" normalises to "Department for Health" — sorts before Transport
    bodies = [
        _make_body(PublicBodyId.DEPARTMENT_FOR_TRANSPORT, "Department for Transport"),
        _make_body(
            PublicBodyId.DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE,
            "Department of Health and Social Care",
        ),
    ]
    port = MagicMock(spec=ListPublicBodiesPort)
    port.list_public_bodies.return_value = bodies

    result = ListPublicBodiesUseCase(list_public_bodies_port=port).execute()

    assert [b.public_body_description for b in result] == [
        "Department of Health and Social Care",
        "Department for Transport",
    ]


def test_execute_bare_department_entry_sorts_before_department_for_of_entries():
    # "Department Devolved" has no for/of — 'd' < 'f' so it precedes all "Department for/of" entries
    bodies = [
        _make_body(PublicBodyId.DEPARTMENT_FOR_TRANSPORT, "Department for Transport"),
        _make_body(
            PublicBodyId.DEPARTMENT_DEVOLVED_TO_WALES, "Department Devolved to Wales"
        ),
        _make_body(
            PublicBodyId.DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE,
            "Department of Health and Social Care",
        ),
    ]
    port = MagicMock(spec=ListPublicBodiesPort)
    port.list_public_bodies.return_value = bodies

    result = ListPublicBodiesUseCase(list_public_bodies_port=port).execute()

    assert [b.public_body_description for b in result] == [
        "Department Devolved to Wales",
        "Department of Health and Social Care",
        "Department for Transport",
    ]


def test_execute_sorts_non_department_entries_by_full_name():
    bodies = [
        _make_body(PublicBodyId.HOME_OFFICE, "Home Office"),
        _make_body(PublicBodyId.CABINET_OFFICE, "Cabinet Office"),
        _make_body(PublicBodyId.HM_TREASURY, "HM Treasury"),
    ]
    port = MagicMock(spec=ListPublicBodiesPort)
    port.list_public_bodies.return_value = bodies

    result = ListPublicBodiesUseCase(list_public_bodies_port=port).execute()

    assert [b.public_body_description for b in result] == [
        "Cabinet Office",
        "HM Treasury",
        "Home Office",
    ]


def test_execute_returns_empty_list_when_no_public_bodies_exist():
    port = MagicMock(spec=ListPublicBodiesPort)
    port.list_public_bodies.return_value = []

    result = ListPublicBodiesUseCase(list_public_bodies_port=port).execute()

    assert result == []
