"""Pydantic models for email personalisation data."""

from pydantic import BaseModel, ConfigDict, Field


class NotifyApplicationSubmitTemplatePersonalisation(BaseModel):
    """
    Application data formatted to fill in GovNotify email template for submission confirmation.

    All fields are strings as required by the "Application submission" email template viewable in the LAA Inquests team in GovNotify.
    See the template page in Confluence for details on default values.
    """

    model_config = ConfigDict(extra="forbid")

    # LAA reference
    laa_reference: str = Field(description="Application LAA reference number")

    # Client details
    client_first_name: str = Field(description="Client's first name")
    client_last_name: str = Field(description="Client's last name")
    client_last_name_at_birth: str = Field(
        default="N/A", description="Client's last name at birth"
    )
    date_of_birth: str = Field(description="Client's date of birth")
    national_insurance_number: str = Field(
        default="N/A", description="Client's National Insurance number"
    )
    has_applied_previously: str = Field(
        description="Whether client has applied previously (Yes/No)"
    )
    prev_application_reference: str = Field(
        default="N/A", description="Previous application reference number"
    )
    client_home_address: str = Field(description="Client's home address")
    correspondence_address: str = Field(description="Correspondence address")
    correspondence_recipient: str = Field(description="Correspondence recipient")
    client_relationship_to_deceased: str = Field(
        description="Client's relationship to deceased"
    )

    # Proceeding details
    proceeding_description: str = Field(description="Proceeding description")
    matter_type: str = Field(description="Matter type")

    # Deceased details
    deceased_first_name: str = Field(description="Deceased person's first name")
    deceased_last_name: str = Field(description="Deceased person's last name")
    deceased_date_of_birth: str = Field(description="Deceased person's date of birth")
    deceased_date_of_death: str = Field(description="Deceased person's date of death")
    # TODO: pass in further information from Deceased table if present as value for deceased_related_applications_information, otherwise
    deceased_related_applications_information: str = Field(
        description="Further info on linked or associated inquests applications concerning the deceased"
    )
    # TODO: if deceased_related_applications_information provided, then set to "Yes"
    deceased_has_other_related_applications: str = Field(
        default="No",
        description="Boolean representing existence of other applications linked to deceased person",
    )
    coroners_reference: str = Field(description="Coroner's reference number")

    # Public authority details
    public_body_description: str = Field(description="Public body description")

    # Evidence (not currently tracked in model)
    file_name: str = Field(default="N/A", description="Uploaded file names")
