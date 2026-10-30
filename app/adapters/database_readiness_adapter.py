import logging
import time
from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.logging_utils import build_log_extra, duration_ms
from app.ports.check_readiness_port import (
    CheckReadinessPort,
    ReadinessUnavailableError,
)

logger = logging.getLogger(__name__)


class DatabaseReadinessAdapter(CheckReadinessPort):
    def __init__(
        self, session_factory: Callable[[], AbstractContextManager[Session]]
    ) -> None:
        self.session_factory = session_factory

    def check(self) -> None:
        started_at = time.perf_counter()
        try:
            with self.session_factory() as session:
                if session.get_bind().dialect.name == "postgresql":
                    session.execute(text("SET LOCAL statement_timeout = '1000ms'"))
                session.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            logger.warning(
                "Database readiness check failed",
                extra=build_log_extra(
                    event="database_readiness_failed",
                    route="/status",
                    method="GET",
                    status_code=503,
                    duration_ms=duration_ms(started_at),
                    exception_type=type(exc).__name__,
                ),
            )
            raise ReadinessUnavailableError("Service unavailable") from exc
