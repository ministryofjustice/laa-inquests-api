from datetime import datetime, UTC

from pydantic import BaseModel, ConfigDict, Field as PydanticField, model_validator
from pydantic.alias_generators import to_camel
from sqlalchemy import Column
from sqlmodel import Enum, Field, SQLModel

from app.models.claim.enums import ClaimStatus, ClaimType, POAType


class ClaimBase(SQLModel):
    laa_reference: int = Field(foreign_key="application.laa_reference")
    claim_type_id: ClaimType = Field(sa_column=Column(Enum(ClaimType)))
    status_id: ClaimStatus = Field(
        default=ClaimStatus.PENDING, sa_column=Column(Enum(ClaimStatus))
    )
    submission_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_profit_cost_net: int
    total_profit_cost_gross: int
    claimant_id: str | None = None
    poa_type_id: POAType | None = Field(
        default=None, sa_column=Column(Enum(POAType), nullable=True)
    )


class Claim(ClaimBase, table=True):
    claim_id: int | None = Field(default=None, primary_key=True)


# REQUEST BODY -- Create
class ClaimCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    claim_type: ClaimType = PydanticField(examples=["PAYMENT_ON_ACCOUNT"])
    total_profit_cost_net: int = PydanticField(examples=[1000])
    total_profit_cost_gross: int = PydanticField(examples=[1200])
    poa_type_id: POAType | None = PydanticField(default=None, examples=["PROFIT_COST"])
    claimant_id: str | None = PydanticField(
        default=None, examples=["claimant-123@provider.co.uk"]
    )

    @model_validator(mode="after")
    def validate_poa_type_id(self) -> "ClaimCreate":
        if self.claim_type == ClaimType.PAYMENT_ON_ACCOUNT:
            if self.poa_type_id is None:
                raise ValueError(
                    "poa_type_id is required when claim_type is PAYMENT_ON_ACCOUNT"
                )
        elif self.poa_type_id is not None:
            raise ValueError(
                "poa_type_id must not be provided when claim_type is not PAYMENT_ON_ACCOUNT"
            )
        return self


# RESPONSE BODY
class ClaimResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )
    claim_id: int
    laa_reference: int
    claim_type_id: ClaimType
    status_id: ClaimStatus
    submission_date: datetime
    total_profit_cost_net: int
    total_profit_cost_gross: int
    claimant_id: str | None = None
    poa_type_id: POAType | None = None
