"""Shared formatting helpers for Gov Notify personalisation building."""

from app.models.claim.enums import ClaimType
from app.use_cases.notify.constants import CLAIM_TYPE_LABELS


def format_submitted_at(submitted_at) -> str:
    """Format datetime into Gov Notify display format like '18 June 2026 14:03 UTC'."""
    return f"{submitted_at.day} {submitted_at.strftime('%B %Y %H:%M UTC')}"


def format_claim_type(claim_type: ClaimType) -> str:
    return CLAIM_TYPE_LABELS[claim_type]
