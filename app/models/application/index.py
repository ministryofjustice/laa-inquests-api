from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy import Column
from sqlmodel import Field, Relationship, SQLModel, Enum
from datetime import datetime, UTC
from app.models.application.enums import ProceedingId


class Proceeding(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    proceeding_id: ProceedingId = Field(
        sa_column=Column(Enum(ProceedingId), unique=True)
    )
    proceeding_description: str | None = "This is the proceeding description"
    category_of_law: str | None = "INQUESTS"
    certificate_type: str | None = "SUBSTANTIVE"
    level_of_service: str | None = "FULL_REPRESENTATION"
    matter_type: str | None = "INQUESTS"
    scope_limitation_heading: str | None = "FINAL_HEARING"
    scope_description: str | None = "This is the scope description"
    substantive_cost_limitation: int | None = 25000
    application_proceedings: list["ApplicationProceeding"] = Relationship(
        back_populates="proceeding"
    )


class ApplicationBase(SQLModel):
    laa_reference: int | None = Field(default_factory=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )
    status: str | None = "LIVE"
    used_delegated_functions: bool = True
    application_type: str | None = "INITIAL"
    auto_grant: bool | None = True
    overall_decision: str | None = "PENDING"


class Application(ApplicationBase, table=True):
    proceedings: list["ApplicationProceeding"] = Relationship(
        back_populates="application"
    )


class ApplicationProceeding(SQLModel, table=True):
    __tablename__ = "application_proceeding"
    application_proceeding_id: int | None = Field(default=None, primary_key=True)
    client_involvement_type: str | None = "RESPONDENT"
    merits_decision: str | None = "PENDING"
    laa_reference: int = Field(foreign_key="application.laa_reference")
    proceeding_id: ProceedingId = Field(foreign_key="proceeding.proceeding_id")
    proceeding: Proceeding = Relationship(back_populates="application_proceedings")
    application: Application = Relationship(back_populates="proceedings")

    @property
    def proceeding_description(self):
        return self.proceeding.proceeding_description

    @property
    def category_of_law(self):
        return self.proceeding.category_of_law

    @property
    def certificate_type(self):
        return self.proceeding.certificate_type

    @property
    def level_of_service(self):
        return self.proceeding.level_of_service

    @property
    def matter_type(self):
        return self.proceeding.matter_type

    @property
    def scope_limitation_heading(self):
        return self.proceeding.scope_limitation_heading

    @property
    def scope_description(self):
        return self.proceeding.scope_description

    @property
    def substantive_cost_limitation(self):
        return self.proceeding.substantive_cost_limitation


# client

# deceased

# public bodies


class ProceedingCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    proceeding_id: str


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    # documents: list[Document]
    # provider: Provider
    # client: Client
    proceedings: list[ProceedingCreate]


class ProceedingResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )
    proceeding_id: str
    proceeding_description: Optional[str] = None
    category_of_law: str
    certificate_type: str
    level_of_service: str
    matter_type: str
    scope_limitation_heading: str
    scope_description: str
    substantive_cost_limitation: int
    client_involvement_type: str
    merits_decision: str


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )
    laa_reference: int
    created_at: datetime
    updated_at: datetime
    status: str
    used_delegated_functions: bool
    application_type: str
    auto_grant: bool
    overall_decision: str
    proceedings: list[ProceedingResponse] = []
