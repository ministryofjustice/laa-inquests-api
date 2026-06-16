"""Use case for building email personalisation data from Application objects."""

from app.models.application.index import Application, Address
from app.models.notifications.personalisation import EmailPersonalisation
from app.config import Config


def build_email_personalisation(application: Application) -> EmailPersonalisation:
    """
    Build personalisation dictionary for GovNotify email template from Application.

    Args:
        application: Application object with all relationships loaded

    Returns:
        Dictionary with all template variables required by GovNotify template
    """
    client = application.client
    deceased = application.deceased

    # Helper to format addresses
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

    # Get home address
    if client.home_address:
        home_address = format_address(client.home_address)
    else:
        home_address = "No fixed abode"

    # Get correspondence address
    if client.correspondence_address:
        correspondence_address = format_address(client.correspondence_address)
    else:
        correspondence_address = "Same as home address"

    # Get correspondence recipient
    if client.is_client_correspondence_recipient:
        correspondence_recipient = "Client"
    else:
        recipient_type = (
            client.correspondence_recipient_type.value
            if client.correspondence_recipient_type
            else "Unknown"
        )
        recipient_name = client.correspondence_recipient_name or "Unknown"
        correspondence_recipient = f"{recipient_name} ({recipient_type})"

    # Get first proceeding (template expects single proceeding)
    proceeding = application.proceedings[0] if application.proceedings else None
    proceeding_description = proceeding.proceeding_description if proceeding else "N/A"
    matter_type = proceeding.matter_type if proceeding else "N/A"

    # Get first public body (template expects single public body or comma-separated list)
    if application.public_bodies:
        public_body_descriptions = [
            pb.public_body_description for pb in application.public_bodies
        ]
        public_body_description = ", ".join(public_body_descriptions)
    else:
        public_body_description = "N/A"

    return EmailPersonalisation(
        # LAA reference
        laa_reference=str(application.laa_reference),
        # Client details
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
        # Proceeding details
        proceeding_description=proceeding_description,
        matter_type=matter_type,
        # Deceased details
        deceased_first_name=deceased.deceased_first_name,
        deceased_last_name=deceased.deceased_last_name,
        deceased_date_of_birth=deceased.deceased_date_of_birth,
        deceased_date_of_death=deceased.deceased_date_of_death,
        deceased_related_applications_information=deceased.further_information or "",
        deceased_has_other_related_applications="Yes"
        if deceased.further_information
        else "No",
        coroners_reference=deceased.coroners_reference,
        # Public authority details
        public_body_description=public_body_description,
        # Evidence (not currently tracked in model)
        file_name="N/A",
        # Feedback link (from config)
        feedback_link=Config.FEEDBACK_LINK,
    )
