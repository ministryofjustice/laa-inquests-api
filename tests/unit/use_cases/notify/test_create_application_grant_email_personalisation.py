import pytest
from pydantic import ValidationError

from app.models.gov_notify_templates.application_grant_personalisation import (
    NotifyApplicationGrantTemplatePersonalisation,
)
from app.use_cases.notify.create_application_grant_email_personalisation import (
    create_application_grant_email_personalisation,
)
from tests.unit.factories import (
    create_base_application,
    create_base_application_proceeding,
    create_base_client,
)


def _create_test_application_and_proceeding():
    client = create_base_client()

    application = create_base_application(client=client)

    proceeding = create_base_application_proceeding(application=application)

    return application, proceeding


def test_create_application_grant_email_personalisation_returns_all_required_fields():
    application, proceeding = _create_test_application_and_proceeding()
    certificate_payload = {"file": "dGVzdA==", "filename": None}

    result = create_application_grant_email_personalisation(
        application, proceeding, certificate_payload
    )

    assert isinstance(result, NotifyApplicationGrantTemplatePersonalisation)
    assert result.laa_reference == "12345"
    assert result.issue_date == "18 June 2026"
    assert result.link_to_file == certificate_payload


def test_create_application_grant_email_personalisation_rejects_missing_required_fields():
    """
    Test that NotifyApplicationGrantTemplatePersonalisation model rejects creation with missing required fields.
    """
    with pytest.raises(ValidationError):
        NotifyApplicationGrantTemplatePersonalisation(
            laa_reference="12345",
        )


def test_create_application_grant_email_personalisation_rejects_extra_fields():
    """
    Test that NotifyApplicationGrantTemplatePersonalisation model rejects creation with extra/unexpected fields.
    """
    with pytest.raises(ValidationError):
        NotifyApplicationGrantTemplatePersonalisation(
            laa_reference="12345",
            issue_date="18 June 2026",
            link_to_file={"file": "dGVzdA=="},
            unexpected_field="This should not be allowed",
        )
