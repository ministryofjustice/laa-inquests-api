import os
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.db import CustomSessionLocal
from app.models.application.enums import (
    AddressSource,
    CorrespondenceRecipientType,
    MeritsDecision,
    ProceedingId,
    PublicBodyId,
)
from app.models.application.index import (
    Address,
    Application,
    ApplicationProceeding,
    ApplicationPublicBody,
    Client,
    CoronersLetter,
    Deceased,
    Provider,
)
from app.models.claim.enums import ClaimStatus, ClaimType, POAType
from app.models.claim.index import Claim, ClaimEvidence

SEED_FIRM_CODE = "1473"
SEED_CORONERS_LETTER_ID = uuid.UUID("5e0bb75e-00e8-4e3d-84b3-88b77ba3aad4")
SEED_CLAIM_EVIDENCE_ID = uuid.UUID("7b34cf18-1d41-40eb-8bc8-9a2e7e14dea6")


def seed_dev():
    """
    Seeds a single granted application with a submitted claim (and their related
    records) into the database.
    Idempotent: keyed on the seed coroners letter id, so it is safe to re-run.
    """
    with CustomSessionLocal() as db_session:
        if db_session.get(CoronersLetter, SEED_CORONERS_LETTER_ID) is not None:
            return

        coroners_letter = CoronersLetter(
            coroners_letter_id=SEED_CORONERS_LETTER_ID,
            sds_file_name="seed-coroners-letter",
            file_name="coroners-letter.pdf",
        )
        db_session.add(coroners_letter)

        correspondence_address = Address(
            address_line_1="123 Example Street",
            address_line_2="Jones",
            town_or_city="Example Town",
            county="Jones",
            postcode="AA1 1AA",
        )
        home_address = Address(
            address_line_1="123 Example Street",
            address_line_2="Jones",
            town_or_city="Example Town",
            county="Jones",
            postcode="AA1 1AA",
        )
        db_session.add(correspondence_address)
        db_session.add(home_address)
        db_session.flush()

        client = Client(
            client_first_name="Jane",
            client_last_name="Smith",
            client_last_name_at_birth="Jones",
            date_of_birth="2000-01-01",
            national_insurance_number="AA123456A",
            has_applied_previously=False,
            prev_application_reference="TBD",
            correspondence_address_source=AddressSource.USE_SPECIFIED_ADDRESS,
            correspondence_address_id=correspondence_address.address_id,
            home_address_id=home_address.address_id,
            has_no_fixed_abode=False,
            is_client_correspondence_recipient=False,
            correspondence_recipient_type=CorrespondenceRecipientType.PERSON,
            correspondence_recipient_name="string",
        )
        db_session.add(client)
        db_session.flush()

        deceased = Deceased(
            deceased_first_name="John",
            deceased_last_name="Smith",
            deceased_date_of_birth="2000-01-01",
            deceased_date_of_death="2025-01-01",
            coroners_reference="Example reference number",
            further_information="Further information.",
            client_relationship_to_deceased="Spouse",
            client_id=client.client_id,
        )
        db_session.add(deceased)
        db_session.flush()

        provider = Provider(
            firm_code=SEED_FIRM_CODE,
            office_id="0U651L",
            email_address="provider@example.com",
        )
        db_session.add(provider)
        db_session.flush()

        application_proceeding = ApplicationProceeding(
            proceeding_id=ProceedingId.IQPC,
            merits_decision=MeritsDecision.GRANTED,
            certificate_start_date=date(2025, 1, 1),
            certificate_issue_date=datetime.now(UTC).date(),
        )
        public_bodies = [
            ApplicationPublicBody(
                public_body_id=PublicBodyId.DEPARTMENT_OF_HEALTH_AND_SOCIAL_CARE
            )
        ]

        application = Application(
            client_id=client.client_id,
            deceased_id=deceased.deceased_id,
            provider_id=provider.provider_id,
            coroners_letter_id=SEED_CORONERS_LETTER_ID,
            proceeding=application_proceeding,
            public_bodies=public_bodies,
            laa_reference="INQ-YYY-YYY",
        )
        db_session.add(application)
        db_session.flush()

        claim = Claim(
            application_id=application.application_id,
            claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
            status_id=ClaimStatus.SUBMITTED,
            total_profit_cost_net=Decimal("1000.00"),
            total_profit_cost_gross=Decimal("1200.00"),
            total_profit_cost_vat_zero=Decimal("500.00"),
            poa_type_id=POAType.PROFIT_COST,
            claimant_id="claimant-123@provider.co.uk",
            claim_evidence=[
                ClaimEvidence(
                    claim_evidence_id=SEED_CLAIM_EVIDENCE_ID,
                    sds_file_name="seed-claim-evidence",
                    file_name="claim-evidence.pdf",
                )
            ],
        )
        db_session.add(claim)
        db_session.commit()


if __name__ == "__main__":
    seed_dev()
