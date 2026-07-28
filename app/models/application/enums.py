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
    IQPC = "IQPC"
    IQPO = "IQPO"
    IQMT = "IQMT"
    IQMH = "IQMH"
    IQMC = "IQMC"
    IQCC = "IQCC"
    IQHO = "IQHO"
    IQCA = "IQCA"
    IQDV = "IQDV"
    IQED = "IQED"
    IQTR = "IQTR"
    IQOT = "IQOT"


class PublicBodyId(str, enum.Enum):
    ATTORNEY_GENERAL = "Attorney General's Office"
    CABINET_OFFICE = "Cabinet Office"
    DEPARTMENT_DEVOLVED_TO_WALES = "Department Devolved to Wales"
    DEPARTMENT_FOR_BUSINESS_AND_TRADE = "Department for Business and Trade"
    DEPARTMENT_FOR_CULTURE_MEDIA_AND_SPORT = "Department for Culture, Media, and Sport"
    DEPARTMENT_FOR_EDUCATION = "Department for Education"
    DEPARTMENT_FOR_ENERGY_SECURITY_AND_NET_ZERO = (
        "Department for Energy Security and Net Zero"
    )
    DEPARTMENT_FOR_ENVIRONMENT_FOOD_AND_RURAL_AFFAIRS = (
        "Department for Environment, Food and Rural Affairs"
    )
    DEPARTMENT_FOR_HOUSING_COMMUNITIES_AND_LOCAL_GOVERNMENT = (
        "Department for Housing, Communities and Local Government"
    )
    DEPARTMENT_FOR_SCIENCE_INNOVATION_AND_TECHNOLOGY = (
        "Department for Science, Innovation and Technology"
    )
    DEPARTMENT_FOR_TRANSPORT = "Department for Transport"
    DEPARTMENT_FOR_WORK_AND_PENSIONS = "Department for Work and Pensions"
    DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE = "Department of Health and Social Care"
    FOREIGN_COMMONWEALTH_AND_DEVELOPMENT_OFFICE = (
        "Foreign, Commonwealth and Development Office"
    )
    HM_TREASURY = "HM Treasury"
    HOME_OFFICE = "Home Office"
    MINISTRY_OF_DEFENCE = "Ministry of Defence"
    MINISTRY_OF_JUSTICE = "Ministry of Justice"
