from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select
from typing import Sequence

# from app.auth.security import get_current_active_user
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
    Deceased,
    MeritsDecisionUpdate,
    ProceedingId,
    PublicBodyId,
)
# from app.models.user import User


router = APIRouter(
    prefix="/applications",
    tags=["Applications"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{laa_reference}", response_model=ApplicationResponse)
async def read_application(
    laa_reference: str,
    session: Session = Depends(get_session),
    # current_user: User = Depends(get_current_active_user),
) -> Application:
    """Get information about a given application."""
    application = session.get(Application, int(laa_reference))
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.get("/")
async def read_all_applications(
    session: Session = Depends(get_session),
    # current_user: User = Depends(get_current_active_user),
) -> Sequence[Application]:
    """Read all the applications currently in the database."""
    applications = session.exec(select(Application)).all()
    return applications


@router.post("/", response_model=ApplicationResponse, status_code=201)
def create_application(
    request: ApplicationCreate,
    session: Session = Depends(get_session),
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
        session.commit()
        session.refresh(home_address_to_add)
        home_address_id = home_address_to_add.address_id
    else:
        session.commit()

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
    )
    session.add(new_client)
    session.commit()
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
    session.commit()
    session.refresh(new_deceased)

    new_application = Application(
        client_id=new_client.client_id,
        deceased_id=new_deceased.deceased_id,
        proceedings=proceedings_to_add,
        public_bodies=public_bodies_to_add,
    )
    session.add(new_application)
    session.commit()
    session.refresh(new_application)
    return new_application


@router.patch("/{laa_reference}/merits-decision", status_code=204)
def patch_merits_decision(
    laa_reference: str,
    request: MeritsDecisionUpdate,
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
    session.add(proceeding)
    session.commit()
    return Response(status_code=204)
