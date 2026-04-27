# All models defining DB Table schemas should be imported into this module this allows them to be
# found by Alembic when auto-generating migrations.
from .application.index import Application  # noqa: F401
from .user import User  # noqa: F401

__all__ = ["Application", "User"]
