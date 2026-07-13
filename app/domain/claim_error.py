import enum


class ClaimErrorCode(str, enum.Enum):
    MISSING_TOTAL_CLAIM_COST = "MISSING_TOTAL_CLAIM_COST"
    MISSING_GROSS_TOTAL_WHEN_NET_ENTERED = "MISSING_GROSS_TOTAL_WHEN_NET_ENTERED"
    PROFIT_COST_MIXED_VAT = "PROFIT_COST_MIXED_VAT"
    NET_TOTAL_HIGHER_THAN_GROSS_TOTAL = "NET_TOTAL_HIGHER_THAN_GROSS_TOTAL"
    NEGATIVE_NET_COST = "NEGATIVE_NET_COST"


class ClaimValidationError(Exception):
    def __init__(self, code: ClaimErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
