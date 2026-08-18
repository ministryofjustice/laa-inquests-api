"""Pydantic model for claim rejection email personalisation data."""

from pydantic import BaseModel, ConfigDict, Field


class NotifyClaimRejectTemplatePersonalisation(BaseModel):
    """Data required by the Gov Notify claim rejection template."""

    model_config = ConfigDict(extra="forbid")

    cert_ref_number: str = Field(description="Certificate number")
    provider_name: str = Field(description="Firm name")
    client_first_name: str = Field(description="Client first name")
    client_last_name: str = Field(description="Client last name")
    claim_submitted_at: str = Field(description="Date and time the claim was submitted")
    claim_type: str = Field(description="Human-readable claim type")
    total_claim_amount: str = Field(description="Total amount claimed")
    date_of_rejection: str = Field(description="Date and time the claim was rejected")
    justification: str = Field(description="Reason the claim was rejected")
