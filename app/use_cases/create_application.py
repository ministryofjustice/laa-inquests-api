from sqlmodel import Session

from app.models.application.index import (
    Address,
    AddressSource,
    Application,
    ApplicationCreate,
    ApplicationProceeding,
    ApplicationPublicBody,
    Client,
    CoronersLetter,
    CoronersLetterResponse,
    Deceased,
    ProceedingId,
    Provider,
    PublicBodyId,
)


class CreateApplicationUseCase:
    def __init__(self, session: Session) -> None:
        self.session = session

    def execute(
        self,
        request: ApplicationCreate,
        coroners_letter_response: CoronersLetterResponse,
    ) -> Application:
        proceedings_to_add = []
        public_bodies_to_add = []

        for proceeding in request.proceedings:
            code_str = proceeding.proceeding_id
            proceeding_to_add = ApplicationProceeding(
                proceeding_id=ProceedingId(code_str)
            )
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
            self.session.add(correspondence_address)

        home_address_id = None
        if request.client.home_address is not None:
            home_address_to_add = Address(**request.client.home_address.model_dump())
            self.session.add(home_address_to_add)
            self.session.commit()
            self.session.refresh(home_address_to_add)
            home_address_id = home_address_to_add.address_id
        else:
            self.session.commit()

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
        self.session.commit()
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
        self.session.commit()
        self.session.refresh(new_deceased)

        new_provider = Provider(
            firm_code=request.provider.firm_code,
            office_id=request.provider.office_id,
        )
        self.session.add(new_provider)
        self.session.commit()
        self.session.refresh(new_provider)

        new_coroners_letter = CoronersLetter(
            sds_id=coroners_letter_response.id,
            file_name=coroners_letter_response.file_name,
        )
        self.session.add(new_coroners_letter)
        self.session.commit()
        self.session.refresh(new_coroners_letter)

        new_application = Application(
            client_id=new_client.client_id,
            deceased_id=new_deceased.deceased_id,
            proceedings=proceedings_to_add,
            public_bodies=public_bodies_to_add,
            provider_id=new_provider.provider_id,
            coroners_letter_id=new_coroners_letter.coroners_letter_id,
        )
        self.session.add(new_application)
        self.session.commit()
        self.session.refresh(new_application)
        return new_application
