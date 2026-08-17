"""Pydantic model for claim rejection email personalisation data."""

from pydantic import BaseModel, ConfigDict, Field


class NotifyClaimRejectTemplatePersonalisation(BaseModel):
    """Data required by the Gov Notify claim rejection template."""

    model_config = ConfigDict(extra="forbid")

    laa_reference: str = Field(description="LAA application reference")
    claim_reference: str = Field(description="Claim reference")
    claim_submitted_at: str = Field(description="Date and time the claim was submitted")
    reject_reason: str = Field(description="Reason the claim was rejected")
