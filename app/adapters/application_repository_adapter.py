import base64
import logging
import re
import uuid

from sqlmodel import Session, exists, select

from app.config import Config
from app.domain.coroners_letter import CoronersLetter
from app.logging_utils import build_log_extra
from app.models.application.enums import MeritsDecision
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
from app.ports.application_backlog_port import ApplicationBacklogPort
from app.ports.create_application_port import CreateApplicationPort
from app.ports.get_application_port import GetApplicationPort
from app.ports.list_applications_port import ListApplicationsPort
from app.ports.list_public_bodies_port import ListPublicBodiesPort
from app.ports.search_application_port import SearchApplicationPort
from app.ports.update_decision_port import ApplicationDecisionPort
from app.ports.upload_coroners_letter_port import UploadCoronersLetterPort

import random
import string

logger = logging.getLogger(__name__)


class ApplicationRepositoryAdapter(
    GetApplicationPort,
    CreateApplicationPort,
    ApplicationDecisionPort,
    ListApplicationsPort,
    ListPublicBodiesPort,
    SearchApplicationPort,
    UploadCoronersLetterPort,
    ApplicationBacklogPort,
):
    def __init__(self, session: Session) -> None:
        self.session = session
        # TODO: Dependency injection of reading whole banned words file into memory so it is done only once.
        with open(Config.BANNED_WORDS_FILE_PATH, "r") as banned_word_file:
            banned_words = [
                base64.b64decode(line.strip()).decode("utf-8")
                for line in banned_word_file
                if line.strip()  # Skip empty lines
            ]
        self.banned_words = [
            word.upper()
            for word in banned_words
            if re.match(
                r"^(?:Q[^B8G6I10OQDS5Z2]{0,8}|[^B8G6I10OQDS5Z2]{1,9})$", word.upper()
            )
        ]
        self.banned_words_pattern = re.compile(
            pattern=r"(?:"
            + "|".join(re.escape(word) for word in self.banned_words)
            + ")"
        )

    def get_application_by_laa_reference(
        self, laa_reference: str
    ) -> Application | None:
        application = self.session.get(Application, int(laa_reference))
        logger.info(
            "Application lookup completed",
            extra=build_log_extra(
                event="application_repository_get_completed",
                laa_reference=laa_reference,
                found=application is not None,
            ),
        )
        return application

    def list_applications(self) -> list[Application]:
        return self.session.exec(select(Application)).all()

    def list_public_bodies(self) -> list[PublicBody]:
        return self.session.exec(select(PublicBody)).all()

    def search_applications(
        self,
        laa_reference: str,
        firm_code: str,
        merits_decision: MeritsDecision | None = None,
    ) -> list[Application]:
        try:
            laa_reference_int = int(laa_reference)
        except ValueError:
            return []

        statement = (
            select(Application)
            .join(Deceased, Application.deceased_id == Deceased.deceased_id)
            .join(Provider, Application.provider_id == Provider.provider_id)
            .join(
                ApplicationProceeding,
                Application.laa_reference == ApplicationProceeding.laa_reference,
            )
            .where(Application.laa_reference == laa_reference_int)
            .where(Provider.firm_code == firm_code)
        )

        if merits_decision is not None:
            statement = statement.where(
                ApplicationProceeding.merits_decision == merits_decision
            )

        return list(self.session.exec(statement).all())

    def create_application(
        self, request: ApplicationCreate, firm_code: str
    ) -> Application:
        application_proceeding = ApplicationProceeding(
            proceeding_id=ProceedingId(request.proceeding.proceeding_id)
        )

        public_bodies_to_add = []

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
                if request.client.correspondence_recipient is not None
                else None
            ),
            correspondence_recipient_name=(
                request.client.correspondence_recipient.recipient_name
                if request.client.correspondence_recipient is not None
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
            firm_code=firm_code,
            office_id=request.provider.office_id,
            email_address=request.provider.email_address,
        )
        self.session.add(new_provider)
        self.session.flush()
        self.session.refresh(new_provider)

        new_application = Application(
            client_id=new_client.client_id,
            deceased_id=new_deceased.deceased_id,
            proceeding=application_proceeding,
            public_bodies=public_bodies_to_add,
            provider_id=new_provider.provider_id,
            coroners_letter_id=request.coroners_letter_id,
            new_laa_reference=self._get_laa_reference(),
        )
        self.session.add(new_application)
        self.session.flush()
        self.session.refresh(new_application)
        logger.info(
            "Application created in repository",
            extra=build_log_extra(
                event="application_repository_create_completed",
                laa_reference=new_application.laa_reference,
                firm_code=firm_code,
            ),
        )
        return new_application

    def _get_laa_reference(self) -> str:
        # TODO: Set maximum number of attempts to avoid infinite loop
        laa_reference = self._generate_laa_reference()
        # Check if the generated reference contains any banned words
        if self.banned_words_pattern.search(laa_reference.replace("-", "")):
            return self._get_laa_reference()
        # Check if the generated reference already exists in the database
        elif self.session.scalar(
            select(exists().where(Application.new_laa_reference == laa_reference))
        ):
            return self._get_laa_reference()
        return laa_reference

    def _generate_laa_reference(self) -> str:
        """
        Generates a unique LAA reference number in the format 'INQ-XXX-XXX'
        """
        # [A-Z0-9]{3}-[A-Z0-9]{3} where each X is a random uppercase letter or digit.
        # Exclude ambiguous characters like I, O, 0, 1 to avoid confusion.
        return f"INQ-{''.join(self._random_char() for _ in range(3))}-{''.join(self._random_char() for _ in range(3))}"

    def _random_char(self):
        chars = [
            c
            for c in string.ascii_uppercase + string.digits
            if c not in "B8G6I10OQDS5Z2"
        ]
        return random.choice(chars)

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

        logger.info(
            "Coroners letter persisted",
            extra=build_log_extra(
                event="application_repository_coroners_letter_saved",
                coroners_letter_id=str(coroners_letter_id),
            ),
        )

        return coroners_letter_id

    def update_decision(
        self,
        proceeding: ApplicationProceeding,
    ) -> None:
        self.session.add(proceeding)
        self.session.flush()
        logger.info(
            "Application decision updated",
            extra=build_log_extra(
                event="application_repository_update_decision_completed",
                laa_reference=proceeding.laa_reference,
                merits_decision=proceeding.merits_decision,
            ),
        )

    def get_pending_applications(self) -> list[Application]:
        statement = (
            select(Application)
            .join(
                ApplicationProceeding,
                Application.laa_reference == ApplicationProceeding.laa_reference,
            )
            .where(ApplicationProceeding.merits_decision == "PENDING")
            .order_by(Application.created_at.asc())
        )
        return list(self.session.exec(statement).unique().all())
