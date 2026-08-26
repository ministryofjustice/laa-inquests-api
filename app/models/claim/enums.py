import enum


class ClaimType(str, enum.Enum):
    PAYMENT_ON_ACCOUNT = "PAYMENT_ON_ACCOUNT"
    FINAL_BILL = "FINAL_BILL"
    NIL_BILL = "NIL_BILL"


class ClaimStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    PAY_IN_FULL = "PAY_IN_FULL"
    REJECTED = "REJECTED"
    REJECTED_WITH_AMENDMENT = "REJECTED_WITH_AMENDMENT"


class POAType(str, enum.Enum):
    PROFIT_COST = "PROFIT_COST"
    EXPERT_COST = "EXPERT_COST"
    NON_EXPERT_DISBURSEMENT = "NON_EXPERT_DISBURSEMENT"


class NumberOfCounselInstructed(str, enum.Enum):
    ZERO = "0"
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    MORE_THAN_6 = "MORE_THAN_6"


class ClaimDecisionStatus(str, enum.Enum):
    REJECT = "REJECT"
    GRANT = "GRANT"
    PAY_IN_FULL = "PAY_IN_FULL"
    PENDING = "PENDING"


class ReasonCode(str, enum.Enum):
    MAX_POA_CLAIMS_EXCEEDED = "MAX_POA_CLAIMS_EXCEEDED"
    CLAIM_EXCEEDS_SUBSTANTIVE_COST_LIMIT = "CLAIM_EXCEEDS_SUBSTANTIVE_COST_LIMIT"
    APPLICATION_CLAIMS_EXCEED_COST_LIMIT = "APPLICATION_CLAIMS_EXCEED_COST_LIMIT"
    PROFIT_COST_POA_CLAIM_SUBMITTED_TOO_EARLY = (
        "PROFIT_COST_POA_CLAIM_SUBMITTED_TOO_EARLY"
    )
    MANUAL_REJECTION = "MANUAL_REJECTION"


class InquestOutcomeId(str, enum.Enum):
    ACCIDENT_OR_MISADVENTURE = "Accident or misadventure"
    ALCOHOL_OR_DRUGS_RELATED = "Alcohol or drugs related"
    INDUSTRIAL_DISEASE = "Industrial disease"
    NARRATIVE_CONCLUSION = "Narrative conclusion"
    NATURAL_CAUSES = "Natural causes"
    OPEN_CONCLUSION = "Open conclusion"
    ROAD_TRAFFIC_COLLISION = "Road traffic collision"
    STILLBIRTH = "Stillbirth"
    SUICIDE = "Suicide"
    UNLAWFUL_OR_LAWFUL_KILLING = "Unlawful or lawful killing"
