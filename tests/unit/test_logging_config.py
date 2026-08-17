import json
import logging

from app.config.logging import JsonLogFormatter


def test_json_log_formatter_includes_custom_extra_fields():
    logger = logging.getLogger("test.logger")
    record = logger.makeRecord(
        name=logger.name,
        level=logging.INFO,
        fn=__file__,
        lno=10,
        msg="Claim created in repository",
        args=(),
        exc_info=None,
        extra={
            "event": "claim_repository_create_completed",
            "laa_reference": "LAA-123",
            "claim_id": 99,
        },
    )

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["laa_reference"] == "LAA-123"
    assert payload["claim_id"] == 99
