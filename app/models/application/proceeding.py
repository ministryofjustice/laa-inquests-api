from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class Proceeding(SQLModel, table=True):
    proceeding_id: str = Field(index=True, unique=True, primary_key=True)
    proceeding_description: str | None = "This is the proceeding description"
    category_of_law: str | None = "INQUESTS"
    certificate_type: str | None = "SUBSTANTIVE"
    level_of_service: str | None = "FULL_REPRESENTATION"
    matter_type: str | None = "INQUESTS"
    scope_limitation_heading: str | None = "FINAL_HEARING"
    scope_description: str | None = "This is the scope description"
    substantive_cost_limitation: int | None = 25000


class ProceedingRequest(BaseModel):
    proceedingId: str
    proceedingDescription: str
    matterType: str
