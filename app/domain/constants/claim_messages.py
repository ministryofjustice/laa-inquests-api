MIXED_VAT_MESSAGE = "You cannot submit a profit cost claim with both 0% and 20% VAT"
MISSING_GROSS_MESSAGE = "Please complete the gross total value of your claim"
MISSING_NON_PROFIT_COST_TOTAL_MESSAGE = (
    "Please complete the total value of your claim to continue"
)
MISSING_TOTAL_MESSAGE = (
    "Either total_profit_cost_vat_zero or both "
    "total_profit_cost_net and total_profit_cost_gross must be provided"
)
NEGATIVE_NET_MESSAGE = "net cost must not be negative"
NET_GT_GROSS_MESSAGE = "Net total cannot be higher than the gross total value"
MISSING_POA_TYPE_MESSAGE = (
    "poa_type_id is required when claim_type is PAYMENT_ON_ACCOUNT"
)
POA_NOT_ALLOWED_MESSAGE = (
    "poa_type_id must not be provided when claim_type is not PAYMENT_ON_ACCOUNT"
)
MAX_POA_CLAIMS_EXCEEDED_MESSAGE = "Maximum number of POA claims exceeded"
APPLICATION_NOT_GRANTED_MESSAGE = (
    "Claims may only be submitted for applications that have been granted"
)
