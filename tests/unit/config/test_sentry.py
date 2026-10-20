import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx
import pytest
import sentry_sdk
from psycopg2.errors import UniqueViolation
from pydantic import BaseModel, ValidationError
from sentry_sdk.transport import Transport
from sqlalchemy.exc import IntegrityError

from app.config.sentry import sentry_config
from app.use_cases.exceptions import (
    ApplicationNotFoundError,
    ClaimEvidenceUploadError,
    CoronersLetterDeleteError,
    SDSClaimEvidenceRetrievalError,
    SDSLetterRetrievalError,
)


def _resolved_data_collection():
    client = sentry_sdk.Client(**{**sentry_config, "dsn": None})
    return client.options["data_collection"]


def test_sentry_config_is_accepted_by_the_sdk():
    sentry_sdk.Client(**{**sentry_config, "dsn": None})


def test_sentry_config_does_not_use_deprecated_send_default_pii():
    assert "send_default_pii" not in sentry_config


def test_data_collection_is_provided_by_user():
    assert _resolved_data_collection()["provided_by_user"] is True


def test_data_collection_disables_user_info():
    assert _resolved_data_collection()["user_info"] is False


def test_data_collection_disables_cookies():
    assert _resolved_data_collection()["cookies"]["mode"] == "off"


def test_data_collection_disables_request_headers():
    assert _resolved_data_collection()["http_headers"]["request"]["mode"] == "off"


def test_data_collection_disables_http_bodies():
    assert _resolved_data_collection()["http_bodies"] == []


def test_data_collection_disables_url_query_params():
    assert _resolved_data_collection()["url_query_params"]["mode"] == "off"


def test_data_collection_disables_database_query_data():
    assert _resolved_data_collection()["database_query_data"] is False


def test_data_collection_disables_queues():
    assert _resolved_data_collection()["queues"] is False


def test_data_collection_disables_stack_frame_variables():
    assert _resolved_data_collection()["stack_frame_variables"] is False


def test_data_collection_disables_gen_ai_and_graphql():
    data_collection = _resolved_data_collection()

    assert data_collection["gen_ai"] == {"inputs": False, "outputs": False}
    assert data_collection["graphql"] == {"document": False, "variables": False}


@pytest.fixture
def captured_items():
    items: list[tuple[str, dict]] = []

    class CapturingTransport(Transport):
        def capture_envelope(self, envelope):
            items.extend((item.type, item.payload.json) for item in envelope.items)

    sentry_sdk.init(
        **{
            **sentry_config,
            "dsn": "https://key@o0.ingest.sentry.io/1",
            "transport": CapturingTransport,
            "traces_sample_rate": 1.0,
        }
    )
    yield items
    sentry_sdk.flush()
    sentry_sdk.get_global_scope().set_client(None)


def _events(items):
    return [payload for item_type, payload in items if item_type == "event"]


def test_logs_are_not_sent_to_sentry(captured_items):
    logging.getLogger("test.sentry").warning("file Jane Doe passport.pdf")
    sentry_sdk.flush()

    assert [t for t, _ in captured_items if t == "log"] == []


def test_info_and_warning_logs_do_not_become_breadcrumbs(captured_items):
    logger = logging.getLogger("test.sentry")
    logger.info("info", extra={"extra": {"file_name": "Jane Doe passport.pdf"}})
    logger.warning("Rate limit exceeded for client 203.0.113.7")
    logger.error("something failed")
    sentry_sdk.flush()

    (event,) = _events(captured_items)
    assert not event.get("breadcrumbs", {}).get("values")


def test_error_logs_still_create_events(captured_items):
    logging.getLogger("test.sentry").error("something failed")
    sentry_sdk.flush()

    assert len(_events(captured_items)) == 1


@pytest.mark.parametrize("logger_name", ["uvicorn.access", "httpx"])
def test_noisy_loggers_are_ignored(captured_items, logger_name):
    logging.getLogger(logger_name).error('203.0.113.7:5432 - "GET /x?y=1"')
    sentry_sdk.flush()

    assert _events(captured_items) == []


def test_sqlalchemy_error_values_are_filtered(captured_items):
    try:
        try:
            raise UniqueViolation("Key (national_insurance_number)=(QQ123456C) exists")
        except UniqueViolation as exc:
            raise IntegrityError(
                "INSERT INTO client (client_first_name) VALUES (%(name)s)",
                {"name": "Jane"},
                exc,
            ) from exc
    except IntegrityError:
        sentry_sdk.capture_exception()
    sentry_sdk.flush()

    (event,) = _events(captured_items)
    payload = json.dumps(event["exception"])
    assert "Jane" not in payload
    assert "QQ123456C" not in payload
    assert "INSERT INTO" not in payload
    assert [v["type"] for v in event["exception"]["values"]] == [
        "UniqueViolation",
        "IntegrityError",
    ]


def test_pydantic_validation_error_values_are_filtered(captured_items):
    class Client(BaseModel):
        first_name: int

    try:
        Client(first_name="Jane")
    except ValidationError:
        sentry_sdk.capture_exception()
    sentry_sdk.flush()

    (event,) = _events(captured_items)
    assert "Jane" not in json.dumps(event["exception"])


def test_other_exception_values_are_kept(captured_items):
    try:
        raise ValueError("unexpected state")
    except ValueError:
        sentry_sdk.capture_exception()
    sentry_sdk.flush()

    (event,) = _events(captured_items)
    assert event["exception"]["values"][0]["value"] == "unexpected state"


def test_error_log_extra_keeps_only_allowlisted_keys(captured_items):
    logging.getLogger("test.sentry").error(
        "upload failed",
        extra={
            "extra": {
                "event": "claim_evidence_upload_failed",
                "request_id": "req-1",
                "correlation_id": "corr-1",
                "status_code": 500,
                "file_name": "Jane Doe passport.pdf",
                "laa_reference": "LAA-1234567",
                "firm_code": "1A234B",
                "route": "/applications/LAA-1234567",
            }
        },
    )
    sentry_sdk.flush()

    (event,) = _events(captured_items)
    assert event["extra"] == {
        "event": "claim_evidence_upload_failed",
        "request_id": "req-1",
        "correlation_id": "corr-1",
        "status_code": 500,
        "laa_reference": "LAA-1234567",
        "firm_code": "1A234B",
        "route": "/applications/LAA-1234567",
    }


def test_error_log_extra_still_drops_file_name(captured_items):
    logging.getLogger("test.sentry").error(
        "upload failed",
        extra={"extra": {"event": "x", "file_name": "Jane Doe passport.pdf"}},
    )
    sentry_sdk.flush()

    (event,) = _events(captured_items)
    assert "file_name" not in event["extra"]


def test_error_log_extra_is_dropped_when_log_has_no_structured_extra(captured_items):
    logging.getLogger("test.sentry").error(
        "failed", extra={"file_name": "Jane Doe passport.pdf"}
    )
    sentry_sdk.flush()

    (event,) = _events(captured_items)
    assert "Jane" not in json.dumps(event.get("extra", {}))


def test_httpx_error_values_are_filtered(captured_items):
    try:
        raise httpx.ConnectError("failed: https://sds/get_file?file_key=Jane_Doe.pdf")
    except httpx.ConnectError:
        sentry_sdk.capture_exception()
    sentry_sdk.flush()

    (event,) = _events(captured_items)
    assert "Jane" not in json.dumps(event["exception"])


@pytest.mark.parametrize(
    "error_class",
    [
        CoronersLetterDeleteError,
        SDSLetterRetrievalError,
        ClaimEvidenceUploadError,
        SDSClaimEvidenceRetrievalError,
    ],
)
def test_file_error_values_are_filtered(captured_items, error_class):
    try:
        raise error_class("while handling file key Jane_Doe_passport.pdf")
    except error_class:
        sentry_sdk.capture_exception()
    sentry_sdk.flush()

    (event,) = _events(captured_items)
    assert "Jane" not in json.dumps(event["exception"])
    assert event["exception"]["values"][0]["type"] == error_class.__name__


def test_non_file_use_case_error_values_are_kept(captured_items):
    try:
        raise ApplicationNotFoundError("Application INQ-123-456 not found")
    except ApplicationNotFoundError:
        sentry_sdk.capture_exception()
    sentry_sdk.flush()

    (event,) = _events(captured_items)
    assert (
        event["exception"]["values"][0]["value"] == "Application INQ-123-456 not found"
    )


class _OkHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


@pytest.fixture
def local_http_server():
    server = HTTPServer(("127.0.0.1", 0), _OkHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def _call_sds_like_urls(base_url: str) -> None:
    httpx.get(f"{base_url}/get_file", params={"file_key": "Jane_Doe_passport.pdf"})
    with httpx.stream(
        "GET", f"{base_url}/bucket/Jane_Doe_passport.pdf?X-Amz-Signature=sig123"
    ) as response:
        list(response.iter_bytes())


def test_outbound_http_breadcrumbs_keep_only_the_host(
    captured_items, local_http_server
):
    _call_sds_like_urls(local_http_server)
    sentry_sdk.capture_message("after calls")
    sentry_sdk.flush()

    (event,) = _events(captured_items)
    crumbs = event["breadcrumbs"]["values"]
    assert [crumb["data"]["url"] for crumb in crumbs] == [local_http_server] * 2
    assert "http.query" not in json.dumps(crumbs)
    for secret in ("Jane", "passport", "sig123", "file_key"):
        assert secret not in json.dumps(event)


def test_outbound_http_spans_keep_only_the_host(captured_items, local_http_server):
    with sentry_sdk.start_transaction(name="probe"):
        _call_sds_like_urls(local_http_server)
    sentry_sdk.flush()

    (transaction,) = [p for t, p in captured_items if t == "transaction"]
    http_spans = [s for s in transaction["spans"] if s["op"] == "http.client"]
    assert len(http_spans) == 2
    for span in http_spans:
        assert span["description"] == f"GET {local_http_server}"
        assert span["data"]["url"] == local_http_server
    for secret in ("Jane", "passport", "sig123", "file_key"):
        assert secret not in json.dumps(transaction)
