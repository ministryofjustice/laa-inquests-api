import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic import (
    Field as PydanticField,
)
from pydantic.alias_generators import to_camel
from sqlalchemy import Column
from sqlmodel import Enum, Field, Relationship, SQLModel

from app.domain.constants.claims import SUBSTANTIVE_CERTIFICATE_AMOUNT
from app.models.application.constants import UNGRANTED_SUBSTANTIVE_COST_LIMITATION
from app.models.application.enums import (
    AddressSource,
    CorrespondenceRecipientType,
    MeritsDecision,
    ProceedingId,
    PublicBodyId,
    ReasonForRefusal,
)


# RELATIONS
class Proceeding(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    proceeding_id: ProceedingId = Field(
        sa_column=Column(Enum(ProceedingId), unique=True)
    )
    proceeding_name: str | None = "This is the proceeding name"
    proceeding_description: str | None = "This is the proceeding description"

    category_of_law: str | None = "INQUESTS"
    certificate_type: str | None = "SUBSTANTIVE"
    level_of_service: str | None = "FULL_REPRESENTATION"
    matter_type: str | None = "INQUESTS"
    scope_limitation_heading: str | None = "FINAL_HEARING"
    scope_description: str | None = "This is the scope description"
    substantive_cost_limitation: int | None = SUBSTANTIVE_CERTIFICATE_AMOUNT
    application_proceeding: "ApplicationProceeding" = Relationship(
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
    has_applied_previously: bool = False
    prev_application_reference: str | None = None
    has_no_fixed_abode: bool = False
    correspondence_address_source: AddressSource = Field(
        sa_column=Column(Enum(AddressSource))
    )


class AddressBase(SQLModel):
    address_line_1: str
    address_line_2: str | None = None
    town_or_city: str
    county: str | None = None
    postcode: str


class DeceasedBase(SQLModel):
    deceased_first_name: str
    deceased_last_name: str
    deceased_date_of_birth: str
    deceased_date_of_death: str
    coroners_reference: str
    further_information: str | None
    client_relationship_to_deceased: str


class Address(AddressBase, table=True):
    address_id: int | None = Field(default=None, primary_key=True)


class Client(ClientBase, table=True):
    client_id: int | None = Field(default=None, primary_key=True)
    applications: list["Application"] = Relationship(back_populates="client")
    deceased: list["Deceased"] = Relationship(back_populates="client")
    correspondence_address_id: int | None = Field(
        default=None, foreign_key="address.address_id"
    )
    home_address_id: int | None = Field(default=None, foreign_key="address.address_id")
    correspondence_address: Optional["Address"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Client.correspondence_address_id]"}
    )
    home_address: Optional["Address"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Client.home_address_id]"}
    )
    correspondence_recipient_type: CorrespondenceRecipientType | None = Field(
        default=None,
        sa_column=Column(Enum(CorrespondenceRecipientType), nullable=True),
    )
    correspondence_recipient_name: str | None = None

    @property
    def correspondence_recipient(self) -> Optional["CorrespondenceRecipientResponse"]:
        if (
            self.correspondence_recipient_type is not None
            and self.correspondence_recipient_name is not None
        ):
            return CorrespondenceRecipientResponse(
                recipient_type=self.correspondence_recipient_type,
                recipient_name=self.correspondence_recipient_name,
            )

        return None


class ProviderBase(SQLModel):
    firm_code: str
    office_id: str
    email_address: str


class Provider(ProviderBase, table=True):
    provider_id: int | None = Field(default=None, primary_key=True)


class ApplicationBase(SQLModel):
    laa_reference: int | None = Field(default_factory=None, primary_key=True)
    new_laa_reference: str = Field(unique=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )
    status: str | None = "LIVE"
    used_delegated_functions: bool = True
    application_type: str | None = "INITIAL"
    auto_grant: bool | None = True


class Deceased(DeceasedBase, table=True):
    deceased_id: int | None = Field(default_factory=None, primary_key=True)
    client_id: int = Field(foreign_key="client.client_id")
    client: Client = Relationship(back_populates="deceased")
    application: Optional["Application"] = Relationship(
        back_populates="deceased", sa_relationship_kwargs={"uselist": False}
    )


class CoronersLetter(SQLModel, table=True):
    __tablename__ = "coroners_letter"
    coroners_letter_id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, unique=True
    )
    sds_file_name: str
    file_name: str


class Application(ApplicationBase, table=True):
    proceeding: "ApplicationProceeding" = Relationship(back_populates="application")
    public_bodies: list["ApplicationPublicBody"] = Relationship(
        back_populates="application",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    client_id: int | None = Field(default=None, foreign_key="client.client_id")
    client: Client | None = Relationship(back_populates="applications")
    deceased_id: int = Field(foreign_key="deceased.deceased_id")
    deceased: Deceased | None = Relationship(
        sa_relationship_kwargs={"uselist": False}, back_populates="application"
    )
    provider_id: int = Field(foreign_key="provider.provider_id")
    provider: Provider | None = Relationship(sa_relationship_kwargs={"uselist": False})

    coroners_letter_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="coroners_letter.coroners_letter_id",
    )
    coroners_letter: CoronersLetter | None = Relationship(
        sa_relationship_kwargs={"uselist": False}
    )

    @computed_field
    @property
    def overall_decision(self) -> str:
        """Calculate overall_decision from the proceeding's merits_decision."""
        return self.proceeding.merits_decision


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
    application_proceeding_id: int = Field(primary_key=True, nullable=False)
    client_involvement_type: str | None = "RESPONDENT"
    merits_decision: str = MeritsDecision.PENDING
    reason_for_refusal: str | None = None
    justification: str | None = None
    laa_reference: int = Field(foreign_key="application.laa_reference")
    proceeding_id: ProceedingId = Field(foreign_key="proceeding.proceeding_id")
    proceeding: Proceeding = Relationship(back_populates="application_proceeding")
    substantive_cost_limitation_effective_date: date = Field(
        nullable=True, default=None
    )
    application: Application = Relationship(back_populates="proceeding")
    certificate_issue_date: date = Field(nullable=True, default=None)
    certificate_start_date: date = Field(nullable=True, default=None)
    certificate_end_date: date = Field(nullable=True, default=None)

    @property
    def proceeding_name(self):
        return self.proceeding.proceeding_name

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
        if self.merits_decision != MeritsDecision.GRANTED:
            return UNGRANTED_SUBSTANTIVE_COST_LIMITATION
        return self.proceeding.substantive_cost_limitation


# REQUEST BODY -- Create
class ProceedingCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    proceeding_id: ProceedingId = PydanticField(examples=["IQPC"])


class AddressCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    address_line_1: str = PydanticField(examples=["123 Example Street"])
    address_line_2: str | None = PydanticField(default=None, examples=["Jones"])
    town_or_city: str = PydanticField(examples=["Example Town"])
    county: str | None = PydanticField(default=None, examples=["Jones"])
    postcode: str = PydanticField(examples=["AA1 1AA"])


class CorrespondenceRecipientCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    recipient_type: CorrespondenceRecipientType
    recipient_name: str


class ClientCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    client_first_name: str = PydanticField(examples=["Jane"])
    client_last_name: str = PydanticField(examples=["Smith"])
    client_last_name_at_birth: str | None = PydanticField(
        default=None, examples=["Jones"]
    )
    date_of_birth: str = PydanticField(examples=["2000-01-01"])
    national_insurance_number: str | None = PydanticField(
        default=None, examples=["AA123456A"]
    )

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth_format(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("date_of_birth must be in YYYY-MM-DD format")
        return v

    has_applied_previously: bool = PydanticField(default=False, examples=[False])
    prev_application_reference: str | None = PydanticField(
        default=None, examples=["TBD"]
    )
    correspondence_address_source: str = PydanticField(
        examples=["USE_SPECIFIED_ADDRESS"]
    )
    correspondence_address: AddressCreate | None = None
    home_address: AddressCreate | None = None
    has_no_fixed_abode: bool = PydanticField(default=False, examples=[False])
    correspondence_recipient: CorrespondenceRecipientCreate | None = None

    @model_validator(mode="after")
    def validate_home_address_against_fixed_abode(self) -> "ClientCreate":
        if self.has_no_fixed_abode and self.home_address is not None:
            raise ValueError(
                "home_address must not be provided when has_no_fixed_abode is true"
            )
        if not self.has_no_fixed_abode and self.home_address is None:
            raise ValueError(
                "home_address is required when has_no_fixed_abode is false"
            )
        return self


class DeceasedCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    deceased_first_name: str = PydanticField(examples=["John"])
    deceased_last_name: str = PydanticField(examples=["Smith"])
    deceased_date_of_birth: str = PydanticField(examples=["2000-01-01"])
    deceased_date_of_death: str = PydanticField(examples=["2025-01-01"])
    coroners_reference: str = PydanticField(examples=["Example reference number"])

    @field_validator("deceased_date_of_birth", "deceased_date_of_death")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("date must be in YYYY-MM-DD format")
        return v

    further_information: str | None = PydanticField(
        default=None, examples=["Further information."]
    )
    client_relationship_to_deceased: str = PydanticField(examples=["Spouse"])


class PublicBodyCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    public_body_id: str = PydanticField(
        examples=["Department of Health and Social Care"]
    )


class ProviderCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    office_id: str = PydanticField(examples=["0U651L"])
    email_address: str = PydanticField(examples=["provider@example.com"])


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    coroners_letter_id: uuid.UUID
    client: ClientCreate
    deceased: DeceasedCreate
    publicBodies: list[PublicBodyCreate]
    proceeding: ProceedingCreate
    provider: ProviderCreate


class RefuseApplicationUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    reason_for_refusal: ReasonForRefusal | None = PydanticField(
        examples=["NOT_IN_SCOPE"]
    )
    justification: str | None = PydanticField(
        examples=["The requested proceeding is out of scope."]
    )

    @model_validator(mode="after")
    def validate_refusal_fields(self) -> "RefuseApplicationUpdate":
        if self.reason_for_refusal is None:
            raise ValueError("reason_for_refusal is required")
        if self.justification is None or not self.justification.strip():
            raise ValueError("justification is required")
        return self


class GrantApplicationUpdate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    certificate_start_date: date = PydanticField(examples=["2000-01-01"])

    @model_validator(mode="after")
    def validate_certificate_start_date(self) -> "GrantApplicationUpdate":
        if self.certificate_start_date > datetime.now(UTC).date():
            raise ValueError("certificate_start_date must not be in the future")
        return self


class UpdateApplicationPublicBodiesRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    public_bodies: list[PublicBodyId]


# RESPONSE BODY
class AddressResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    address_line_1: str
    address_line_2: str | None = None
    town_or_city: str
    county: str | None = None
    postcode: str


class CorrespondenceRecipientResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    recipient_type: CorrespondenceRecipientType
    recipient_name: str


class ClientResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )
    client_id: int
    client_first_name: str
    client_last_name: str
    client_last_name_at_birth: str | None = None
    date_of_birth: str
    national_insurance_number: str | None = None
    correspondence_address_source: str
    correspondence_address: AddressResponse | None = None
    home_address: AddressResponse | None = None
    has_applied_previously: bool = False
    prev_application_reference: str | None = None
    has_no_fixed_abode: bool = False
    correspondence_recipient: CorrespondenceRecipientResponse | None = None


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
    proceeding_name: str | None = None
    proceeding_description: str | None = None
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


class ProviderResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    firm_name: str | None = None
    account_number: str | None = None
    email_address: str


class UploadCoronersLetterResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    coroners_letter_id: uuid.UUID
    coroners_letter_file_name: str


class CoronersLetterResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    file_name: str


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
    proceeding: ProceedingResponse
    public_bodies: list[PublicBodyResponse] = []
    client: ClientResponse
    deceased: DeceasedResponse
    provider: ProviderResponse
    coroners_letter: CoronersLetterResponse | None = None


# Use case models
class ApplicationSearchResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )
    laa_reference: int
    client_first_name: str
    client_last_name: str
    client_date_of_birth: str
    date_submitted: datetime
    firm_name: str
    firm_number: str
    overall_decision: str


@dataclass
class CoronersLetterResult:
    file_name: str
    content: Iterator[bytes]


class SDSUploadCoronersLetterResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )
    sds_file_name: str
    status: str


class SDSUploadClaimEvidenceResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )
    sds_file_name: str
    status: str
