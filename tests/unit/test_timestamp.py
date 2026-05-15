from sqlmodel import Session
from app.models.application.index import Application
from datetime import datetime, UTC


def test_timezone():
    application = Application()
    assert application.created_at.tzinfo == UTC


def test_created_at():
    before_application_creation = datetime.now(UTC)
    application = Application()
    after_application_creation = datetime.now(UTC)
    assert (
        before_application_creation
        < application.created_at
        < after_application_creation
    )


def test_created_at_read_from_db(session: Session):
    before_creation = datetime.now(UTC)
    original_application = Application(deceased_id=1)
    session.add(original_application)
    session.commit()
    application = session.get(Application, original_application.laa_reference)
    assert (
        before_creation
        <= application.created_at.replace(tzinfo=UTC)
        <= datetime.now(UTC)
    )
