import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from pydantic.alias_generators import to_camel
from sqlalchemy import Column, Numeric
from sqlmodel import Enum, Field, Relationship, SQLModel

from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimStatus,
    ClaimType,
    POAType,
    ReasonCode,
)


class ClaimBase(SQLModel):
    laa_reference: int = Field(foreign_key="application.laa_reference")
    claim_type_id: ClaimType = Field(sa_column=Column(Enum(ClaimType)))
    status_id: ClaimStatus = Field(
        default=ClaimStatus.SUBMITTED, sa_column=Column(Enum(ClaimStatus))
    )
    submission_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_profit_cost_net: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(10, 2), nullable=True)
    )
    total_profit_cost_gross: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(10, 2), nullable=True)
    )
    total_profit_cost_vat_zero: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(10, 2), nullable=True)
    )
    claimant_id: str | None = None
    poa_type_id: POAType | None = Field(
        default=None, sa_column=Column(Enum(POAType), nullable=True)
    )


class Claim(ClaimBase, table=True):
    claim_id: int | None = Field(default=None, primary_key=True)
    claim_evidence: list["ClaimEvidence"] = Relationship(back_populates="claim")


class ClaimDecision(SQLModel, table=True):
    __tablename__ = "claim_decision"

    claim_decision_id: int | None = Field(default=None, primary_key=True)
    claim_id: int = Field(foreign_key="claim.claim_id")
    decision: ClaimDecisionStatus = Field(
        sa_column=Column(Enum(ClaimDecisionStatus), nullable=False)
    )
    decision_reasons: list["DecisionReason"] = Relationship(
        back_populates="claim_decision"
    )


class DecisionReason(SQLModel, table=True):
    __tablename__ = "decision_reason"

    decision_reason_id: int | None = Field(default=None, primary_key=True)
    claim_decision_id: int = Field(foreign_key="claim_decision.claim_decision_id")
    reason_code: ReasonCode = Field(sa_column=Column(Enum(ReasonCode), nullable=False))
    justification: str | None = Field(default=None)
    claim_decision: ClaimDecision = Relationship(back_populates="decision_reasons")


class ClaimEvidence(SQLModel, table=True):
    __tablename__ = "claim_evidence"
    claim_evidence_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        unique=True,
    )
    sds_file_name: str
    file_name: str
    claim_id: int | None = Field(default=None, foreign_key="claim.claim_id")
    claim: Optional["Claim"] = Relationship(back_populates="claim_evidence")


# REQUEST BODY -- Create
class ClaimCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    claim_type: ClaimType = PydanticField(examples=["PAYMENT_ON_ACCOUNT"])
    total_profit_cost_net: Decimal | None = PydanticField(
        default=None, examples=["1000.00"]
    )
    total_profit_cost_gross: Decimal | None = PydanticField(
        default=None, examples=["1200.00"]
    )
    total_profit_cost_vat_zero: Decimal | None = PydanticField(
        default=None, examples=["500.00"]
    )
    poa_type_id: POAType | None = PydanticField(default=None, examples=["PROFIT_COST"])
    claimant_id: str | None = PydanticField(
        default=None, examples=["claimant-123@provider.co.uk"]
    )
    claim_evidence_ids: list[uuid.UUID] = PydanticField(
        examples=[["3fa85f64-5717-4562-b3fc-2c963f66afa6"]]
    )


# RESPONSE BODY
class ClaimResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )
    claim_id: int
    rejection_reasons: list[ReasonCode] | None = None


class UploadClaimEvidenceResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    claim_evidence_id: uuid.UUID
    claim_evidence_file_name: str
