import logging

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File
from sqlmodel import Session, select
from typing import Sequence

# from app.auth.security import get_current_active_user
from app.adapters.sds_adapter import SdsAdapter
from app.db import get_session
from app.models.application.index import (
    Address,
    Application,
    ApplicationCreate,
    ApplicationProceeding,
    ApplicationPublicBody,
    ApplicationResponse,
    AddressSource,
    Client,
    CoronersLetter,
    Deceased,
    MeritsDecisionUpdateRefuse,
    ProceedingId,
    Provider,
    PublicBodyId,
    UploadCoronersLetterResponse,
)
from app.models.application.enums import MeritsDecision

from app.adapters.provider_details_adapter import ProviderDetailsAdapter
from app.config import Config
from app.ports.provider_details_port import ProviderDetailsPort
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import ApplicationNotFoundError, CoronersLetterSaveError
from app.use_cases.read_application import ReadApplicationUseCase

# from app.models.user import User
from app.adapters.gov_notify import GovNotifyAdapter, GovNotifyClient
from app.use_cases.save_coroners_letter import SaveCoronersLetterUseCase
from app.adapters.gov_notify import GovNotifyClient
from app.use_cases.notify.send_application_confirmation import (
    send_application_confirmation,
)
from app.use_cases.notify.send_application_refusal import send_application_refusal


router = APIRouter(
    prefix="/applications",
    tags=["Applications"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)


def get_provider_details_port() -> ProviderDetailsPort:
    return ProviderDetailsAdapter(
        base_url=Config.PROVIDER_API_BASE_URL, api_key=Config.PROVIDER_API_KEY
    )


def get_sds_port() -> SdsPort:
    return SdsAdapter(
        base_url=Config.SDS_BASE_URL,
        tenant_id=Config.SDS_TENANT_ID,
        client_id=Config.SDS_CLIENT_ID,
        client_secret=Config.SDS_CLIENT_SECRET,
        scope=Config.SDS_SCOPE,
    )


def get_read_application_use_case(
    session: Session = Depends(get_session),
    provider_details_port: ProviderDetailsPort = Depends(get_provider_details_port),
) -> ReadApplicationUseCase:
    return ReadApplicationUseCase(
        session=session, provider_details_port=provider_details_port
    )


def get_save_coroners_letter_use_case(
    sds_port: SdsPort = Depends(get_sds_port),
) -> SaveCoronersLetterUseCase:
    return SaveCoronersLetterUseCase(sds_port=sds_port)


def get_gov_notify_adapter() -> GovNotifyAdapter:
    return GovNotifyClient()


@router.get("/{laa_reference}", response_model=ApplicationResponse)
async def read_application(
    laa_reference: str,
    use_case: ReadApplicationUseCase = Depends(get_read_application_use_case),
    # current_user: User = Depends(get_current_active_user),
) -> ApplicationResponse:
    """Get information about a given application."""
    try:
        return use_case.execute(laa_reference)
    except ApplicationNotFoundError:
        raise HTTPException(status_code=404, detail="Application not found")


@router.get("/")
async def read_all_applications(
    session: Session = Depends(get_session),
    # current_user: User = Depends(get_current_active_user),
) -> Sequence[Application]:
    """Read all the applications currently in the database."""
    applications = session.exec(select(Application)).all()
    return applications


@router.post(
    "/upload-coroners-letter",
    response_model=UploadCoronersLetterResponse,
    status_code=201,
)
async def upload_coroners_letter(
    file: UploadFile = File(...),
    use_case: SaveCoronersLetterUseCase = Depends(get_save_coroners_letter_use_case),
) -> UploadCoronersLetterResponse:
    """Upload a coroner's letter to document storage and return its file ID."""
    contents = await file.read()
    try:
        response = use_case.execute(
            contents,
            file.filename,
        )
    except CoronersLetterSaveError:
        raise HTTPException(status_code=500, detail="Failed to save coroners letter")
    return UploadCoronersLetterResponse(file_id=response.sds_id)


@router.post("/", response_model=ApplicationResponse, status_code=201)
def create_application(
    request: ApplicationCreate,
    session: Session = Depends(get_session),
    gov_notify_adapter: GovNotifyAdapter = Depends(get_gov_notify_adapter),
    # current_user: User = Depends(get_current_active_user),
) -> Application:
    """Creates a new application with proceedings, public bodies."""
    proceedings_to_add = []
    public_bodies_to_add = []

    for proceeding in request.proceedings:
        code_str = proceeding.proceeding_id
        proceeding_to_add = ApplicationProceeding(proceeding_id=ProceedingId(code_str))
        proceedings_to_add.append(proceeding_to_add)

    for public_body in request.publicBodies:
        public_body_enum = PublicBodyId(public_body.public_body_id)
        public_body_to_add = ApplicationPublicBody(public_body_id=public_body_enum)
        public_bodies_to_add.append(public_body_to_add)

    correspondence_address = None
    if request.client.correspondence_address is not None:
        correspondence_address = Address(
            **request.client.correspondence_address.model_dump()
        )
        session.add(correspondence_address)

    home_address_id = None
    if request.client.home_address is not None:
        home_address_to_add = Address(**request.client.home_address.model_dump())
        session.add(home_address_to_add)
        session.flush()
        session.refresh(home_address_to_add)
        home_address_id = home_address_to_add.address_id
    else:
        session.flush()

    correspondence_address_id = None
    if correspondence_address is not None:
        session.refresh(correspondence_address)
        correspondence_address_id = correspondence_address.address_id

    client_data = request.client.model_dump(
        exclude={"correspondence_address", "home_address"}
    )
    client_data["correspondence_address_source"] = AddressSource(
        client_data["correspondence_address_source"]
    )

    new_client = Client(
        **client_data,
        correspondence_address_id=correspondence_address_id,
        home_address_id=home_address_id,
        correspondence_recipient_type=(
            request.client.correspondence_recipient.recipient_type
            if not request.client.is_client_correspondence_recipient
            and request.client.correspondence_recipient is not None
            else None
        ),
        correspondence_recipient_name=(
            request.client.correspondence_recipient.recipient_name
            if not request.client.is_client_correspondence_recipient
            and request.client.correspondence_recipient is not None
            else None
        ),
    )
    session.add(new_client)
    session.flush()
    session.refresh(new_client)

    new_deceased = Deceased(
        deceased_first_name=request.deceased.deceased_first_name,
        deceased_last_name=request.deceased.deceased_last_name,
        deceased_date_of_birth=request.deceased.deceased_date_of_birth,
        deceased_date_of_death=request.deceased.deceased_date_of_death,
        coroners_reference=request.deceased.coroners_reference,
        further_information=request.deceased.further_information,
        client_relationship_to_deceased=request.deceased.client_relationship_to_deceased,
        client_id=new_client.client_id,
    )
    session.add(new_deceased)
    session.flush()
    session.refresh(new_deceased)

    new_provider = Provider(
        firm_code=request.provider.firm_code,
        office_id=request.provider.office_id,
        email_address=request.provider.email_address,
    )
    session.add(new_provider)
    session.flush()
    session.refresh(new_provider)

    new_coroners_letter = CoronersLetter(
        sds_id=request.coroners_letter_id,
        file_name=request.coroners_letter_id,
    )
    session.add(new_coroners_letter)
    session.flush()
    session.refresh(new_coroners_letter)

    new_application = Application(
        client_id=new_client.client_id,
        deceased_id=new_deceased.deceased_id,
        proceedings=proceedings_to_add,
        public_bodies=public_bodies_to_add,
        provider_id=new_provider.provider_id,
        coroners_letter_id=new_coroners_letter.coroners_letter_id,
    )
    session.add(new_application)

    # Flush to generate laa_reference without committing transaction
    session.flush()
    session.refresh(new_application)

    try:
        send_application_confirmation(
            gov_notify_adapter, new_application, request.provider.email_address
        )
        session.commit()
    except Exception:
        # Rollback database changes if email fails
        session.rollback()
        raise

    session.refresh(new_application)
    return new_application


@router.patch("/{laa_reference}/merits-decision", status_code=204)
def patch_merits_decision(
    laa_reference: str,
    request: MeritsDecisionUpdateRefuse,
    session: Session = Depends(get_session),
    # current_user: User = Depends(get_current_active_user),
) -> Response:
    """Set the merits decision on the single proceeding for a given application."""
    application = session.get(Application, int(laa_reference))
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    if not application.proceedings:
        raise HTTPException(
            status_code=404, detail="No proceedings found for application"
        )

    proceeding = application.proceedings[0]
    proceeding.merits_decision = request.merits_decision
    proceeding.reason_for_refusal = (
        request.reason_for_refusal.value if request.reason_for_refusal else None
    )
    proceeding.justification = request.justification

    application.overall_decision = request.merits_decision

    session.add(application)
    session.add(proceeding)

    decision = MeritsDecision(request.merits_decision)

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise

    if decision == MeritsDecision.REFUSED:
        try:
            gov_notify_adapter = GovNotifyClient()
            send_application_refusal(
                gov_notify_adapter,
                application,
                proceeding,
                application.provider.email_address,
            )
        except Exception:
            logger.warning(
                "Failed to send refusal email for application %s",
                application.laa_reference,
                exc_info=True,
            )

    return Response(status_code=204)
