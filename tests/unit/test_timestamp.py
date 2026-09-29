from datetime import UTC, datetime

from sqlmodel import Session

from app.models.application.index import Application
from tests.factories.persisted import create_application


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
    original_application = create_application(session)
    application = session.get(Application, original_application.application_id)
    assert (
        before_creation
        <= application.created_at.replace(tzinfo=UTC)
        <= datetime.now(UTC)
    )
