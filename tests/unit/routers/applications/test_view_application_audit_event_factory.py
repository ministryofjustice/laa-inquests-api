from unittest.mock import ANY, MagicMock

from app.models.audit.index import ViewApplicationAudit
from app.routers.dependencies.view_application_audit_event_factory import (
    ViewApplicationAuditEventFactory,
)


def test_builds_view_application_audit_event_for_the_requested_application():
    audit_event = ViewApplicationAuditEventFactory(page="overview")(
        user_email_address="user@example.com",
        request=MagicMock(path_params={"laa_reference": "LAA123"}),
    )

    assert audit_event == ViewApplicationAudit(
        timestamp=ANY,
        user_email_address="user@example.com",
        laa_reference="LAA123",
        page="overview",
    )
