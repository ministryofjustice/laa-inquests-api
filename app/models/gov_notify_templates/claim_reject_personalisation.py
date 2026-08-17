"""Pydantic model for claim rejection email personalisation data."""

from pydantic import BaseModel, ConfigDict, Field


class NotifyClaimRejectTemplatePersonalisation(BaseModel):
    """Data required by the Gov Notify claim rejection template."""

    model_config = ConfigDict(extra="forbid")

    laa_reference: str = Field(description="LAA application reference")
    claim_id: str = Field(description="Claim identifier")
    client_first_name: str = Field(description="Client first name")
    client_last_name: str = Field(description="Client last name")
    claim_submitted_at: str = Field(description="Date and time the claim was submitted")
    justification: str = Field(description="Reason the claim was rejected")
