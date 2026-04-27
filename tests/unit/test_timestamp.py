from sqlmodel import Session
from app.models.application.index import Application
from datetime import datetime, UTC


def test_timezone():
    application = Application(
        status="PENDING",
        laa_reference="INQ-000-005",
        used_delegated_functions=True,
        application_type="INITIAL",
        auto_grant=True,
        overall_decision="PENDING",
    )
    assert application.created_at.tzinfo == UTC


def test_created_at():
    before_application_creation = datetime.now(UTC)
    application = Application(
        status="PENDING",
        laa_reference="INQ-000-006",
        used_delegated_functions=True,
        application_type="INITIAL",
        auto_grant=True,
        overall_decision="PENDING",
    )
    after_application_creation = datetime.now(UTC)
    assert (
        before_application_creation
        < application.created_at
        < after_application_creation
    )


def test_created_at_read_from_db(session: Session):
    before_creation = datetime.now(UTC)
    original_application = Application(
        status="PENDING",
        laa_reference="INQ-000-007",
        used_delegated_functions=True,
        application_type="INITIAL",
        auto_grant=True,
        overall_decision="PENDING",
    )
    session.add(original_application)
    session.commit()
    application = session.get(Application, original_application.application_id)
    assert (
        before_creation
        <= application.created_at.replace(tzinfo=UTC)
        <= datetime.now(UTC)
    )
