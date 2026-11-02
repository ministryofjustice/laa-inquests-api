from unittest.mock import ANY, Mock, call, create_autospec

import pytest
from sqlalchemy.exc import OperationalError, SQLAlchemyError, TimeoutError
from sqlmodel import Session

from app.adapters.database_readiness_adapter import DatabaseReadinessAdapter
from app.ports.check_readiness_port import ReadinessUnavailableError


def test_database_readiness_opens_session_and_executes_connectivity_query() -> None:
    session = create_autospec(Session, instance=True)
    session.__enter__.return_value = session
    session_factory = Mock(return_value=session)
    adapter = DatabaseReadinessAdapter(session_factory)

    adapter.check()

    session_factory.assert_called_once_with()
    session.exec.assert_called_once()
    assert str(session.exec.call_args.args[0]).strip().upper() == "SELECT 1"
    session.connection.assert_not_called()
    session.__exit__.assert_called_once_with(None, None, None)


def test_database_readiness_translates_connection_failure() -> None:
    session = create_autospec(Session, instance=True)
    session.__enter__.return_value = session
    session.exec.side_effect = OperationalError(
        "SELECT 1", {}, Exception("Database connection refused")
    )
    adapter = DatabaseReadinessAdapter(Mock(return_value=session))

    with pytest.raises(ReadinessUnavailableError):
        adapter.check()

    session.__exit__.assert_called_once()


@pytest.mark.parametrize(
    "database_error",
    [
        OperationalError("SELECT 1", {}, Exception("Database connection refused")),
        TimeoutError("Database connection timed out"),
    ],
    ids=["connection-failure", "timeout"],
)
def test_database_readiness_translates_session_creation_failure(
    database_error: SQLAlchemyError,
) -> None:
    adapter = DatabaseReadinessAdapter(Mock(side_effect=database_error))

    with pytest.raises(ReadinessUnavailableError) as error:
        adapter.check()

    assert str(error.value) == "Service unavailable"
    assert error.value.__cause__ is database_error


def test_database_readiness_limits_postgresql_query_timeout_to_its_transaction() -> (
    None
):
    session = create_autospec(Session, instance=True)
    session.__enter__.return_value = session
    session.get_bind.return_value.dialect.name = "postgresql"
    adapter = DatabaseReadinessAdapter(Mock(return_value=session))

    adapter.check()

    session.connection.return_value.exec_driver_sql.assert_called_once_with(
        "SET LOCAL statement_timeout = '1000ms'"
    )
    session.exec.assert_called_once()
    assert str(session.exec.call_args.args[0]).strip().upper() == "SELECT 1"
    session.assert_has_calls(
        [
            call.connection(),
            call.connection().exec_driver_sql("SET LOCAL statement_timeout = '1000ms'"),
            call.exec(ANY),
        ]
    )
    session.commit.assert_not_called()
    session.__exit__.assert_called_once_with(None, None, None)
