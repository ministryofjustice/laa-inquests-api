# All models defining DB Table schemas should be imported into this module this allows them to be
# found by Alembic when auto-generating migrations.

from .application.index import (
    Address,
    Application,
    ApplicationProceeding,
    Proceeding,
    Client,
    PublicBody,
    ApplicationPublicBody,
    Deceased,
)  # noqa: F401
from .user import User  # noqa: F401

__all__ = [
    "Address",
    "Proceeding",
    "PublicBody",
    "Deceased",
    "Client",
    "Application",
    "User",
    "ApplicationProceeding",
    "ApplicationPublicBody",
]
