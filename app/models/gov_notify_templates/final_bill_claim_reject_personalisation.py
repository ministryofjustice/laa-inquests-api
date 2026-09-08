"""Pydantic model for final bill claim rejection email personalisation data."""

from pydantic import BaseModel, ConfigDict, Field


class NotifyFinalBillClaimRejectTemplatePersonalisation(BaseModel):
    """Data required by the Gov Notify final bill claim rejection template."""

    model_config = ConfigDict(extra="forbid")

    ref_number: str = Field(description="Legal aid certificate reference")
    provider_name: str = Field(description="Firm name")
    client_first_name: str = Field(description="Client first name")
    client_last_name: str = Field(description="Client last name")
    date_of_claim: str = Field(description="Date and time the claim was submitted")
    claim_type: str = Field(description="Human-readable claim type")
    claim_ref: str = Field(description="Claim reference")
    claimed_amount: str = Field(description="Total amount claimed")
    reason_for_refusal: str = Field(description="Reason the claim was rejected")
    date_of_rejection: str = Field(description="Date and time the claim was rejected")
