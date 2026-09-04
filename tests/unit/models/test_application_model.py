from tests.unit.factories import (
    create_base_application,
    create_base_application_proceeding,
    create_base_application_public_body,
)


def test_application_laa_reference_is_external_reference():
    application = create_base_application(laa_reference="INQ-YYY-YYY")

    assert application.laa_reference == "INQ-YYY-YYY"


def test_application_application_id_is_independent_of_laa_reference():
    application = create_base_application(application_id=None)

    assert application.laa_reference == "INQ-YYY-YYY"


def test_application_proceeding_keeps_internal_application_id():
    application_proceeding = create_base_application_proceeding(application_id=12345)

    assert application_proceeding.application_id == 12345


def test_application_public_body_keeps_internal_application_id():
    application_public_body = create_base_application_public_body(application_id=12345)

    assert application_public_body.application_id == 12345
