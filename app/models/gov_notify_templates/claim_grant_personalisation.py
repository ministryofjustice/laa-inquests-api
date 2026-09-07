"""Pydantic model for POA claim grant email personalisation data."""

from pydantic import BaseModel, ConfigDict, Field


class NotifyClaimGrantTemplatePersonalisation(BaseModel):
    """Data required by the Gov Notify POA claim grant template."""

    model_config = ConfigDict(extra="forbid")

    ref_number: str = Field(description="Legal aid certificate reference")
    provider_name: str = Field(description="Firm name")
    client_first_name: str = Field(description="Client first name")
    client_last_name: str = Field(description="Client last name")
    date_of_claim: str = Field(description="Date and time the claim was submitted")
    claim_type: str = Field(description="Human-readable claim type")
    claim_ref: str = Field(description="Claim reference")
    zero_vat_POA_costs: str = Field(description="Costs charged at 0% VAT")
    net_POA_costs: str = Field(description="Net costs at 20% VAT")
    gross_POA_costs: str = Field(description="Gross costs at 20% VAT")
