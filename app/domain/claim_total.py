from decimal import Decimal


def resolve_claim_total(
    gross: Decimal | None, vat_zero_total: Decimal | None
) -> Decimal | None:
    """Gross already includes any 0% VAT amount, so it is the claim total. A missing
    or 0.00 gross means only the 0% VAT total was entered."""
    if gross is not None and not (gross == 0 and vat_zero_total is not None):
        return gross
    return vat_zero_total
