# All models defining DB Table schemas should be imported into this module this allows them to be
# found by Alembic when auto-generating migrations.

from .application.index import (
    Address,
    Application,
    ApplicationProceeding,
    ApplicationPublicBody,
    Client,
    Deceased,
    Proceeding,
    PublicBody,
)
from .claim.index import (
    Claim,
    ClaimDecision,
    ClaimEvidence,
    DecisionReason,
)
from .user import User

__all__ = [
    "Address",
    "Application",
    "ApplicationProceeding",
    "ApplicationPublicBody",
    "Claim",
    "ClaimDecision",
    "ClaimEvidence",
    "Client",
    "Deceased",
    "DecisionReason",
    "Proceeding",
    "PublicBody",
    "User",
]
