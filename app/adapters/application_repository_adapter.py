import uuid

from sqlmodel import Session, select

from app.domain.coroners_letter import CoronersLetter
from app.models.application.index import (
    Address,
    AddressSource,
    Application,
    ApplicationCreate,
    ApplicationProceeding,
    ApplicationPublicBody,
    Client,
    Deceased,
    ProceedingId,
    Provider,
    PublicBody,
    PublicBodyId,
)
from app.models.application.index import (
    CoronersLetter as CoronersLetterModel,
)
from app.ports.create_application_port import CreateApplicationPort
from app.ports.get_application_port import GetApplicationPort
from app.ports.list_applications_port import ListApplicationsPort
from app.ports.list_public_bodies_port import ListPublicBodiesPort
from app.ports.search_application_port import SearchApplicationPort
from app.ports.update_decision_port import ApplicationDecisionPort
from app.ports.upload_coroners_letter_port import UploadCoronersLetterPort


class ApplicationRepositoryAdapter(
    GetApplicationPort,
    CreateApplicationPort,
    ApplicationDecisionPort,
    ListApplicationsPort,
    ListPublicBodiesPort,
    SearchApplicationPort,
    UploadCoronersLetterPort,
):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_application_by_laa_reference(
        self, laa_reference: str
    ) -> Application | None:
        return self.session.get(Application, int(laa_reference))

    def list_applications(self) -> list[Application]:
        return self.session.exec(select(Application)).all()

    def list_public_bodies(self) -> list[PublicBody]:
        return self.session.exec(select(PublicBody)).all()

    def search_applications(
        self, laa_reference: str, firm_code: str
    ) -> list[Application]:
        try:
            laa_reference_int = int(laa_reference)
        except ValueError:
            return []
        statement = (
            select(Application)
            .join(Provider, Application.provider_id == Provider.provider_id)
            .where(Application.laa_reference == laa_reference_int)
            .where(Provider.firm_code == firm_code)
        )
        return list(self.session.exec(statement).all())

    def create_application(self, request: ApplicationCreate) -> Application:
        proceedings_to_add = []
        public_bodies_to_add = []

        for proceeding in request.proceedings:
            code_str = proceeding.proceeding_id
            proceedings_to_add.append(
                ApplicationProceeding(proceeding_id=ProceedingId(code_str))
            )

        for public_body in request.publicBodies:
            public_bodies_to_add.append(
                ApplicationPublicBody(
                    public_body_id=PublicBodyId(public_body.public_body_id)
                )
            )

        correspondence_address = None
        if request.client.correspondence_address is not None:
            correspondence_address = Address(
                **request.client.correspondence_address.model_dump()
            )
            self.session.add(correspondence_address)

        home_address_id = None
        if request.client.home_address is not None:
            home_address_to_add = Address(**request.client.home_address.model_dump())
            self.session.add(home_address_to_add)
            self.session.flush()
            self.session.refresh(home_address_to_add)
            home_address_id = home_address_to_add.address_id
        else:
            self.session.flush()

        correspondence_address_id = None
        if correspondence_address is not None:
            self.session.refresh(correspondence_address)
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
        self.session.add(new_client)
        self.session.flush()
        self.session.refresh(new_client)

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
        self.session.add(new_deceased)
        self.session.flush()
        self.session.refresh(new_deceased)

        new_provider = Provider(
            firm_code=request.provider.firm_code,
            office_id=request.provider.office_id,
            email_address=request.provider.email_address,
        )
        self.session.add(new_provider)
        self.session.flush()
        self.session.refresh(new_provider)

        new_application = Application(
            client_id=new_client.client_id,
            deceased_id=new_deceased.deceased_id,
            proceedings=proceedings_to_add,
            public_bodies=public_bodies_to_add,
            provider_id=new_provider.provider_id,
            coroners_letter_id=request.coroners_letter_id,
        )
        self.session.add(new_application)
        self.session.flush()
        self.session.refresh(new_application)
        return new_application

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def save_uploaded_coroners_letter(
        self,
        coroners_letter: CoronersLetter,
    ) -> uuid.UUID:
        coroners_letter_model = CoronersLetterModel(
            sds_file_name=coroners_letter.sds_file_name,
            file_name=coroners_letter.file_name,
        )
        self.session.add(coroners_letter_model)
        self.session.flush()
        coroners_letter_id = coroners_letter_model.coroners_letter_id
        self.session.commit()

        return coroners_letter_id

    def update_decision(
        self,
        proceeding: ApplicationProceeding,
    ) -> None:
        self.session.add(proceeding)
        self.session.flush()
