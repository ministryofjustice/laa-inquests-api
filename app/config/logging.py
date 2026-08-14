import json
import logging
from datetime import UTC, datetime

from app.config import Config
from app.logging_utils import log_level_from_name


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "service": getattr(record, "service", Config.SERVICE_NAME),
            "environment": getattr(record, "environment", Config.ENVIRONMENT),
            "event": getattr(record, "event", "log_event"),
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "correlation_id": getattr(record, "correlation_id", None),
            "route": getattr(record, "route", None),
            "method": getattr(record, "method", None),
            "status_code": getattr(record, "status_code", None),
            "duration_ms": getattr(record, "duration_ms", None),
        }

        if record.exc_info:
            payload["exception_type"] = record.exc_info[0].__name__

        for key, value in record.__dict__.items():
            payload[key] = value

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    root_logger = logging.getLogger()
    level = log_level_from_name(Config.LOG_LEVEL)
    root_logger.setLevel(level)

    if not root_logger.handlers:
        logging.basicConfig(level=level)

    is_local = Config.ENVIRONMENT.strip().lower() == "local"
    formatter: logging.Formatter
    if is_local:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        )
    else:
        formatter = JsonLogFormatter()

    for handler in root_logger.handlers:
        handler.setLevel(level)
        handler.setFormatter(formatter)
