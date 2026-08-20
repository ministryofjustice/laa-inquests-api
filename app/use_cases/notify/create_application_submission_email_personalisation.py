"""Use case for building email personalisation data from Application objects."""

from app.models.application.index import Address, Application
from app.models.gov_notify_templates.application_submit_personalisation import (
    NotifyApplicationSubmitTemplatePersonalisation,
)


def create_application_submission_email_personalisation(
    application: Application,
) -> NotifyApplicationSubmitTemplatePersonalisation:
    """
    Build dictionary for populating GovNotify application submission email template.

    Args:
        application: Application object with all relationships loaded

    Returns:
        Dictionary with all template variables required by GovNotify application submission email template
    """
    client = application.client
    deceased = application.deceased

    def format_address(address: Address | None) -> str:
        if not address:
            return "N/A"

        parts = [
            address.address_line_1,
            address.address_line_2,
            address.town_or_city,
            address.county,
            address.postcode,
        ]
        return "\n".join(part for part in parts if part)

    if client.home_address:
        home_address = format_address(client.home_address)
    else:
        home_address = "No fixed abode"

    if client.correspondence_address:
        correspondence_address = format_address(client.correspondence_address)
    else:
        correspondence_address = "Same as home address"

    if not client.correspondence_recipient_name:
        correspondence_recipient = "Client"
    else:
        recipient_type = (
            client.correspondence_recipient_type.value
            if client.correspondence_recipient_type
            else "Unknown"
        )
        recipient_name = client.correspondence_recipient_name or "Unknown"
        correspondence_recipient = f"{recipient_name} ({recipient_type})"

    proceeding_description = application.proceeding.proceeding_description
    matter_type = application.proceeding.matter_type

    if application.public_bodies:
        public_body_descriptions = [
            pb.public_body_description for pb in application.public_bodies
        ]
        public_body_description = ", ".join(public_body_descriptions)
    else:
        public_body_description = "N/A"

    return NotifyApplicationSubmitTemplatePersonalisation(
        laa_reference=str(application.laa_reference),
        client_first_name=client.client_first_name,
        client_last_name=client.client_last_name,
        client_last_name_at_birth=client.client_last_name_at_birth or "Not provided",
        date_of_birth=client.date_of_birth,
        national_insurance_number=client.national_insurance_number or "Not provided",
        has_applied_previously="Yes" if client.has_applied_previously else "No",
        prev_application_reference=client.prev_application_reference or "Not provided",
        client_home_address=home_address or "No fixed abode",
        correspondence_address=correspondence_address,
        correspondence_recipient=correspondence_recipient,
        client_relationship_to_deceased=deceased.client_relationship_to_deceased,
        proceeding_description=proceeding_description,
        matter_type=matter_type,
        deceased_first_name=deceased.deceased_first_name,
        deceased_last_name=deceased.deceased_last_name,
        deceased_date_of_birth=deceased.deceased_date_of_birth,
        deceased_date_of_death=deceased.deceased_date_of_death,
        deceased_related_applications_information=deceased.further_information or "",
        deceased_has_other_related_applications="Yes"
        if deceased.further_information
        else "No",
        coroners_reference=deceased.coroners_reference,
        public_body_description=public_body_description,
        file_name="N/A",
    )
