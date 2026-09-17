from .applications import router as applications
from .claims import router as claims
from .notifications import router as notifications
from .reports import router as reports
from .monitoring import router as monitoring

__all__ = ["applications", "claims", "notifications", "reports", "monitoring"]
