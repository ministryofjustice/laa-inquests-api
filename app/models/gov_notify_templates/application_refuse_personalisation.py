"""Pydantic model for application refusal email personalisation data."""

from pydantic import BaseModel, ConfigDict, Field


class NotifyApplicationRefuseTemplatePersonalisation(BaseModel):
    """Data required by the Gov Notify application refusal template."""

    model_config = ConfigDict(extra="forbid")

    client_first_name: str = Field(description="Client's first name")
    client_last_name: str = Field(description="Client's last name")
    laa_reference: str = Field(description="LAA application reference")
    application_submitted_at: str = Field(
        description="Date and time the application was submitted"
    )
    reason_for_refusal: str = Field(description="Reason the application was refused")
    justification: str = Field(description="Justification for refusal")
