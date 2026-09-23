"""Pydantic model for claim submission email personalisation data."""

from pydantic import BaseModel, ConfigDict, Field


class NotifyClaimSubmitTemplatePersonalisation(BaseModel):
    """Data required by the Gov Notify claim submission template."""

    model_config = ConfigDict(extra="forbid")

    provider_name: str = Field(description="Firm name")
    ref_number: str = Field(description="Legal aid certificate reference")
    client_first_name: str = Field(description="Client first name")
    client_last_name: str = Field(description="Client last name")
    date_of_claim: str = Field(description="Date and time the claim was submitted")
    claim_type: str = Field(description="Human-readable claim type")
    claim_reference: str = Field(description="Claim reference")
    claimed_amount: str = Field(description="Total amount claimed")
