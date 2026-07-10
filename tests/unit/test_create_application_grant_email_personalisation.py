from datetime import UTC, datetime, date

from app.models.application.enums import AddressSource, ProceedingId
from app.models.application.index import Application, ApplicationProceeding, Client
from app.models.gov_notify_templates.application_grant_personalisation import (
    NotifyApplicationGrantTemplatePersonalisation,
)
from app.use_cases.notify.create_application_grant_email_personalisation import (
    create_application_grant_email_personalisation,
)

import pytest


def _create_test_application_and_proceeding(laa_reference: int = 12345):
    client = Client(
        client_id=1,
        client_first_name="Jane",
        client_last_name="Doe",
        date_of_birth="15-06-1985",
        correspondence_address_source=AddressSource.USE_CLIENT_HOME_ADDRESS,
    )

    application = Application(
        laa_reference=laa_reference,
        created_at=datetime(2026, 6, 18, 14, 3, tzinfo=UTC),
        client_id=1,
        client=client,
        deceased_id=1,
        provider_id=1,
    )

    proceeding = ApplicationProceeding(
        application_proceeding_id=1,
        laa_reference=laa_reference,
        proceeding_id=ProceedingId.TEST1,
        merits_decision="GRANTED",
        certificate_issue_date=date(2026, 6, 18),
    )

    return application, proceeding


def test_create_application_grant_email_personalisation_returns_all_required_fields():
    application, proceeding = _create_test_application_and_proceeding(
        laa_reference=12345
    )

    result = create_application_grant_email_personalisation(application, proceeding)

    assert isinstance(result, NotifyApplicationGrantTemplatePersonalisation)
    assert result.team_name == "Legal Aid Advice Inquests"
    assert result.laa_reference == "12345"
    assert result.issue_date == "18 June 2026"


def test_create_application_grant_email_personalisation_rejects_missing_required_fields():
    """
    Test that NotifyApplicationGrantTemplatePersonalisation model rejects creation with missing required fields.
    """
    with pytest.raises(Exception):
        NotifyApplicationGrantTemplatePersonalisation(
            laa_reference="12345",
        )


def test_create_application_grant_email_personalisation_rejects_extra_fields():
    """
    Test that NotifyApplicationGrantTemplatePersonalisation model rejects creation with extra/unexpected fields.
    """
    with pytest.raises(Exception):
        NotifyApplicationGrantTemplatePersonalisation(
            laa_reference="12345",
            team_name="Legal Aid Advice Inquests",
            issue_date="18 June 2026",
            unexpected_field="This should not be allowed",
        )
