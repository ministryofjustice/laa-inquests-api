"""Shared constants for Gov Notify personalisation building."""

from app.models.claim.enums import ClaimType

CLAIM_TYPE_LABELS = {
    ClaimType.PAYMENT_ON_ACCOUNT: "Payment on account",
    ClaimType.FINAL_BILL: "Final bill",
    ClaimType.NIL_BILL: "Nil bill",
}
