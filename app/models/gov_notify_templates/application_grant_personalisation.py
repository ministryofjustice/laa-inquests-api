"""Pydantic model for application grant email personalisation data."""

from pydantic import BaseModel, ConfigDict, Field


class NotifyApplicationGrantTemplatePersonalisation(BaseModel):
    """Data required by the Gov Notify application grant template."""

    model_config = ConfigDict(extra="forbid")

    team_name: str = Field(description="Team name")
    laa_reference: str = Field(description="LAA application reference")
    issue_date: str = Field(description="Certificate issue date")
