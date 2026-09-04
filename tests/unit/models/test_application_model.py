from tests.unit.factories import (
    create_base_application,
    create_base_application_proceeding,
    create_base_application_public_body,
)


def test_application_laa_reference_returns_string_of_application_id():
    application = create_base_application(application_id=12345)

    assert application.laa_reference == "12345"


def test_application_laa_reference_is_none_when_application_id_not_set():
    application = create_base_application(application_id=None)

    assert application.laa_reference is None


def test_application_proceeding_laa_reference_returns_string_of_application_id():
    application_proceeding = create_base_application_proceeding(application_id=12345)

    assert application_proceeding.laa_reference == "12345"


def test_application_public_body_laa_reference_returns_string_of_application_id():
    application_public_body = create_base_application_public_body(application_id=12345)

    assert application_public_body.laa_reference == "12345"
