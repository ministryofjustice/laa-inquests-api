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
MISSING_INQUEST_OUTCOMES_MESSAGE = (
    "At least one inquest outcome is required for final bill and nil bill claims"
)
INQUEST_OUTCOMES_NOT_ALLOWED_MESSAGE = (
    "Inquest outcomes may only be provided for final bill and nil bill claims"
)
MISSING_COST_TEMPLATE_FILE_MESSAGE = (
    "A cost template file is required for final bill claims"
)
COST_TEMPLATE_FILE_NOT_ALLOWED_MESSAGE = (
    "A cost template file may only be provided for final bill claims"
)
MISSING_FINAL_BILL_DETAILS_MESSAGE = (
    "All final bill details are required for final bill and nil bill claims"
)
FINAL_BILL_DETAILS_NOT_ALLOWED_MESSAGE = (
    "Final bill details may only be provided for final bill and nil bill claims"
)
MISSING_COUNSEL_DETAILS_MESSAGE = "Counsel details are required for final bill claims"
COUNSEL_DETAILS_NOT_ALLOWED_MESSAGE = (
    "Counsel details may only be provided for final bill claims"
)
NET_TOTAL_NOT_ALLOWED_FOR_BILL_MESSAGE = (
    "A net total may not be provided for final bill and nil bill claims"
)
VAT_ZERO_TOTAL_NOT_ALLOWED_FOR_BILL_MESSAGE = (
    "A zero-rated VAT total may not be provided for final bill and nil bill claims"
)
MISSING_GROSS_TOTAL_FOR_BILL_MESSAGE = (
    "A gross total is required for final bill and nil bill claims"
)
FINAL_BILL_GROSS_MUST_BE_POSITIVE_MESSAGE = (
    "The gross total must be greater than zero for final bill claims"
)
NIL_BILL_GROSS_MUST_BE_ZERO_MESSAGE = "The gross total must be zero for nil bill claims"
CLAIM_EVIDENCE_NOT_ALLOWED_MESSAGE = (
    "Claim evidence may only be provided for payment on account and final bill claims"
)
