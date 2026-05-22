from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy import Column
from sqlmodel import Field, Relationship, SQLModel, Enum
from datetime import datetime, UTC
from app.models.application.enums import MeritsDecision, ProceedingId, PublicBodyId


# RELATIONS
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


class PublicBody(SQLModel, table=True):
    __tablename__ = "public_body"
    id: int | None = Field(default=None, primary_key=True)
    public_body_id: PublicBodyId = Field(
        sa_column=Column(Enum(PublicBodyId), unique=True)
    )
    public_body_description: str
    application_public_body: list["ApplicationPublicBody"] = Relationship(
        back_populates="public_body"
    )


class ClientBase(SQLModel):
    client_first_name: str
    client_last_name: str
    client_last_name_at_birth: str | None = None
    date_of_birth: str
    national_insurance_number: str | None = None
    correspondence_address: str | None = None
    home_address: str | None = None
    has_applied_previously: bool = False
    prev_application_reference: str | None = None


class DeceasedBase(SQLModel):
    deceased_first_name: str
    deceased_last_name: str
    deceased_date_of_birth: str
    deceased_date_of_death: str
    coroners_reference: str
    further_information: str | None
    client_relationship_to_deceased: str


class Client(ClientBase, table=True):
    client_id: int | None = Field(default=None, primary_key=True)
    applications: list["Application"] = Relationship(back_populates="client")
    deceased: list["Deceased"] = Relationship(back_populates="client")


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


class Deceased(DeceasedBase, table=True):
    deceased_id: int | None = Field(default_factory=None, primary_key=True)
    client_id: int = Field(foreign_key="client.client_id")
    client: Client = Relationship(back_populates="deceased")
    application: Optional["Application"] = Relationship(
        back_populates="deceased", sa_relationship_kwargs={"uselist": False}
    )


class Application(ApplicationBase, table=True):
    proceedings: list["ApplicationProceeding"] = Relationship(
        back_populates="application"
    )
    public_bodies: list["ApplicationPublicBody"] = Relationship(
        back_populates="application"
    )
    client_id: int | None = Field(default=None, foreign_key="client.client_id")
    client: Client | None = Relationship(back_populates="applications")
    deceased_id: int = Field(foreign_key="deceased.deceased_id")
    deceased: Deceased | None = Relationship(
        sa_relationship_kwargs={"uselist": False}, back_populates="application"
    )


class ApplicationPublicBody(SQLModel, table=True):
    __tablename__ = "application_public_body"
    application_public_body_id: int | None = Field(default=None, primary_key=True)
    public_body_id: PublicBodyId = Field(foreign_key="public_body.public_body_id")
    laa_reference: int = Field(foreign_key="application.laa_reference")
    public_body: PublicBody = Relationship(back_populates="application_public_body")
    application: Application = Relationship(back_populates="public_bodies")

    @property
    def public_body_description(self):
        return self.public_body.public_body_description


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


# REQUEST BODY -- Create
class ProceedingCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    proceeding_id: str


class ClientCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    client_first_name: str
    client_last_name: str
    client_last_name_at_birth: Optional[str] = None
    date_of_birth: str
    national_insurance_number: Optional[str] = None
    correspondence_address: Optional[str] = None
    home_address: Optional[str] = None
    has_applied_previously: bool = False
    prev_application_reference: Optional[str] = None


class DeceasedCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    deceased_first_name: str
    deceased_last_name: str
    deceased_date_of_birth: str
    deceased_date_of_death: str
    coroners_reference: str
    further_information: str | None
    client_relationship_to_deceased: str


class PublicBodyCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    public_body_id: str


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    # documents: list[Document]
    # provider: Provider
    client: ClientCreate
    deceased: DeceasedCreate
    publicBodies: list[PublicBodyCreate]
    proceedings: list[ProceedingCreate]


class MeritsDecisionUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    merits_decision: MeritsDecision


# RESPONSE BODY
class ClientResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )
    client_id: int
    client_first_name: str
    client_last_name: str
    client_last_name_at_birth: Optional[str] = None
    date_of_birth: str
    national_insurance_number: Optional[str] = None
    correspondence_address: Optional[str] = None
    home_address: Optional[str] = None
    has_applied_previously: bool = False
    prev_application_reference: Optional[str] = None


class PublicBodyResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )
    public_body_id: str
    public_body_description: str


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


class DeceasedResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    deceased_id: int
    deceased_first_name: str
    deceased_last_name: str
    deceased_date_of_birth: str
    deceased_date_of_death: str
    coroners_reference: str
    further_information: str | None
    client_relationship_to_deceased: str


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
    public_bodies: list[PublicBodyResponse] = []
    client: ClientResponse
    deceased: DeceasedResponse
