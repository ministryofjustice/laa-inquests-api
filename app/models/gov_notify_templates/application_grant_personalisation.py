"""Pydantic model for application grant email personalisation data."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class NotifyApplicationGrantTemplatePersonalisation(BaseModel):
    """Data required by the Gov Notify application grant template."""

    model_config = ConfigDict(extra="forbid")

    laa_reference: str = Field(description="LAA application reference")
    issue_date: str = Field(description="Certificate issue date")
    link_to_file: dict[str, Any] = Field(
        description=(
            "Payload containing the certificate PDF; used as a link_to_file placeholder "
        )
    )
