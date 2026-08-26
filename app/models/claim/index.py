import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator
from pydantic import Field as PydanticField
from pydantic.alias_generators import to_camel
from sqlalchemy import Column, Numeric
from sqlmodel import Enum, Field, Relationship, SQLModel

from app.domain.constants.claims import SUBSTANTIVE_CERTIFICATE_AMOUNT
from app.models.application.index import Application
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimStatus,
    ClaimType,
    InquestOutcomeId,
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
    total_funds_remaining_after_claim: Decimal = Field(
        default=Decimal(SUBSTANTIVE_CERTIFICATE_AMOUNT),
        sa_column=Column(
            Numeric(10, 2),
            nullable=False,
            server_default=str(SUBSTANTIVE_CERTIFICATE_AMOUNT),
        ),
    )
    claimant_id: str | None = None
    poa_type_id: POAType | None = Field(
        default=None, sa_column=Column(Enum(POAType), nullable=True)
    )


class Claim(ClaimBase, table=True):
    claim_id: int | None = Field(default=None, primary_key=True)
    application: Application | None = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )
    claim_evidence: list["ClaimEvidence"] = Relationship(back_populates="claim")
    claim_inquest_outcomes: list["ClaimInquestOutcome"] = Relationship(
        back_populates="claim",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    claim_cost_template: Optional["ClaimCostTemplate"] = Relationship(
        back_populates="claim",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"},
    )

    @property
    def inquest_outcomes(self) -> list[InquestOutcomeId]:
        return [link.inquest_outcome_id for link in self.claim_inquest_outcomes]


class ClaimCostTemplate(SQLModel, table=True):
    __tablename__ = "claim_cost_template"
    claim_cost_template_id: int | None = Field(default=None, primary_key=True)
    claim_id: int = Field(foreign_key="claim.claim_id", unique=True)
    claim_cost_template_file_id: uuid.UUID
    claim_cost_template_file_name: str
    claim: "Claim" = Relationship(back_populates="claim_cost_template")


class ClaimInquestOutcome(SQLModel, table=True):
    __tablename__ = "claim_inquest_outcome"
    claim_inquest_outcome_id: int | None = Field(default=None, primary_key=True)
    claim_id: int = Field(foreign_key="claim.claim_id")
    inquest_outcome_id: InquestOutcomeId = Field(
        sa_column=Column(Enum(InquestOutcomeId), nullable=False)
    )
    claim: "Claim" = Relationship(back_populates="claim_inquest_outcomes")


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
class ClaimCostTemplateFile(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    claim_cost_template_file_id: uuid.UUID = PydanticField(
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"]
    )
    claim_cost_template_file_name: str = PydanticField(
        examples=["claim_cost_template.xlsx"]
    )


class ClaimCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    claim_type: ClaimType = PydanticField(
        examples=["PAYMENT_ON_ACCOUNT", "FINAL_BILL", "NIL_BILL"]
    )
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
    claimant_id: str = PydanticField(examples=["claimant-123@provider.co.uk"])
    claim_evidence_ids: list[uuid.UUID] = PydanticField(
        default_factory=list,
        examples=[["3fa85f64-5717-4562-b3fc-2c963f66afa6"]],
    )
    inquest_outcomes: list[InquestOutcomeId] = PydanticField(
        default_factory=list,
        examples=[["ACCIDENT_OR_MISADVENTURE"]],
    )
    cost_template_file: ClaimCostTemplateFile | None = PydanticField(default=None)

    @field_validator("inquest_outcomes", mode="before")
    @classmethod
    def _parse_inquest_outcomes(cls, value: object) -> list[InquestOutcomeId]:
        if not value:
            return []
        if not isinstance(value, list):
            raise TypeError("inquest_outcomes must be a list")
        parsed: list[InquestOutcomeId] = []
        for item in value:
            if isinstance(item, InquestOutcomeId):
                parsed.append(item)
            elif isinstance(item, str) and item in InquestOutcomeId.__members__:
                parsed.append(InquestOutcomeId[item])
            else:
                raise ValueError(f"Invalid inquest outcome: {item!r}")
        return parsed


# REQUEST BODY -- Reject
class RejectClaimRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    justification: str = PydanticField(examples=["Rejected following manual review."])


# RESPONSE BODY
class ClaimResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )
    claim_id: int
    rejection_reasons: list[ReasonCode] | None = None


class ClaimSummaryBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )
    claim_id: int
    claim_type_id: ClaimType
    submission_date: datetime
    total_profit_cost_net: Decimal | None = None
    total_profit_cost_gross: Decimal | None = None
    total_profit_cost_vat_zero: Decimal | None = None
    total_funds_remaining_after_claim: Decimal
    poa_type_id: POAType | None = None


class ClaimSummaryResponse(ClaimSummaryBase):
    status_id: ClaimStatus
    claim_decision_status: ClaimDecisionStatus | None = None


class ClaimEvidenceResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )
    claim_evidence_id: uuid.UUID
    file_name: str


class DecisionReasonResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )
    reason_code: ReasonCode
    justification: str | None = None


class ClaimDecisionResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )
    claim_decision_id: int
    decision: ClaimDecisionStatus
    decision_reasons: list[DecisionReasonResponse] = []


class CostTemplateFileResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )
    claim_cost_template_file_id: uuid.UUID
    claim_cost_template_file_name: str


class ClaimByIdResponse(ClaimSummaryBase):
    substantive_cost_limitation: int | None = None
    claim_evidence: list[ClaimEvidenceResponse] = []
    claim_decision: ClaimDecisionResponse | None = None
    inquest_outcomes: list[InquestOutcomeId] = []
    cost_template_file: CostTemplateFileResponse | None = None

    @field_serializer("inquest_outcomes")
    def _serialize_inquest_outcomes(self, value: list[InquestOutcomeId]) -> list[str]:
        return [outcome.name for outcome in value]


class UploadClaimEvidenceResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    claim_evidence_id: uuid.UUID
    claim_evidence_file_name: str


@dataclass
class ClaimEvidenceResult:
    file_name: str
    content: Iterator[bytes]
