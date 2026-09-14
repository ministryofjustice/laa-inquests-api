"""Pydantic model for final bill claim paid (granted) email personalisation data."""

from pydantic import BaseModel, ConfigDict, Field


class NotifyFinalBillClaimGrantTemplatePersonalisation(BaseModel):
    """Data required by the Gov Notify final bill claim paid template."""

    model_config = ConfigDict(extra="forbid")

    ref_number: str = Field(description="Legal aid certificate reference")
    provider_name: str = Field(description="Firm name")
    client_first_name: str = Field(description="Client first name")
    client_last_name: str = Field(description="Client last name")
    date_of_claim: str = Field(description="Date and time the claim was submitted")
    claim_type: str = Field(description="Human-readable claim type")
    claim_ref: str = Field(description="Claim reference")
    claimed_amount: str = Field(description="Total amount claimed")
    net_profit_costs: str = Field(description="Net profit costs at 20% VAT")
    gross_profit_costs: str = Field(description="Gross profit costs at 20% VAT")
    zero_vat_profit_costs: str = Field(description="Profit costs at 0% VAT")
    net_disbursement_costs: str = Field(description="Net disbursement costs at 20% VAT")
    gross_disbursement_costs: str = Field(
        description="Gross disbursement costs at 20% VAT"
    )
    zero_vat_disbursement_costs: str = Field(description="Disbursement costs at 0% VAT")
