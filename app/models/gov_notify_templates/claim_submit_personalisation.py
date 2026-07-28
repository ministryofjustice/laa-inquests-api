"""Pydantic model for claim submission email personalisation data."""

from pydantic import BaseModel, ConfigDict, Field


class NotifyClaimSubmitTemplatePersonalisation(BaseModel):
    """Data required by the Gov Notify claim submission template."""

    model_config = ConfigDict(extra="forbid")

    laa_reference: str = Field(description="LAA application reference")
    client_name: str = Field(description="Client full name")
    submission_date: str = Field(description="Claim submission date")