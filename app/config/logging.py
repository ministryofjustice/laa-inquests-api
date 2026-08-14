import json
import logging
from datetime import UTC, datetime

from app.config import Config
from app.logging_utils import log_level_from_name

# COPILOT TODO: Remove this and the check
_RESERVED_LOG_RECORD_KEYS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


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
            if key in _RESERVED_LOG_RECORD_KEYS or key in payload:
                continue
            payload[key] = value

        return json.dumps(payload, default=str)


# COPILOT TODO: This is a big departure from how we were logging before, can we make fewer changes here (e.g. I think StreamHandler is new)
def configure_logging() -> None:
    root_logger = logging.getLogger()
    level = log_level_from_name(Config.LOG_LEVEL, Config.ENVIRONMENT)
    root_logger.setLevel(level)

    if not root_logger.handlers:
        root_logger.addHandler(logging.StreamHandler())

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
