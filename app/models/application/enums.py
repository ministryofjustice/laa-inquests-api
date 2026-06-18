import enum


class MeritsDecision(str, enum.Enum):
    PENDING = "PENDING"
    REFUSED = "REFUSED"
    GRANTED = "GRANTED"


class ReasonForRefusal(str, enum.Enum):
    NOT_IN_SCOPE = "NOT_IN_SCOPE"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    DUPLICATE_CASE = "DUPLICATE_CASE"


class AddressSource(str, enum.Enum):
    USE_CLIENT_HOME_ADDRESS = "USE_CLIENT_HOME_ADDRESS"
    USE_PROVIDER_ADDRESS = "USE_PROVIDER_ADDRESS"
    USE_SPECIFIED_ADDRESS = "USE_SPECIFIED_ADDRESS"


class CorrespondenceRecipientType(str, enum.Enum):
    PERSON = "PERSON"
    ORGANISATION = "ORGANISATION"


class ProceedingId(str, enum.Enum):
    PC049 = "PC049"
    MN035 = "MN035"
    MN036 = "MN036"
    MH028 = "MH028"
    MH030 = "MH030"
    IQ001 = "IQ001"
    IQ002 = "IQ002"
    IQ003 = "IQ003"
    IQ004 = "IQ004"
    IQ010 = "IQ010"
    TEST1 = "TEST1"


class PublicBodyId(str, enum.Enum):
    PRIME_MINISTER_OFFICE = "Prime Minister's Office 10 Downing Street"
    CABINET_OFFICE = "Cabinet Office"
    ATTORNEY_GENERAL = "Attorney General's Office"
    DEPARTMENT_FOR_BUSINESS_AND_TRADE = "Department for Business & Trade"
    DEPARTMENT_FOR_CULTURE_MEDIA_AND_SPORT = "Department for Culture, Media & Sport"
    DEPARTMENT_FOR_EDUCATION = "Department for Education"
    DEPARTMENT_FOR_ENERGY_SECURITY_AND_NET_ZERO = (
        "Department for Energy Security & Net Zero"
    )
    DEPARTMENT_FOR_ENVIRONMENT_FOOD_AND_RURAL_AFFAIRS = (
        "Department for Environment, Food & Rural Affairs"
    )
    DEPARTMENT_FOR_SCIENCE_INNOVATION_AND_TECHNOLOGY = (
        "Department for Science, Innovation & Technology"
    )
    DEPARTMENT_FOR_TRANSPORT = "Department for Transport"
    DEPARTMENT_FOR_WORK_AND_PENSIONS = "Department for Work & Pensions"
    DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE = "Department of Health & Social Care"
