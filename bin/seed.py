import os
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.dialects.postgresql import insert

from app.db import CustomSessionLocal
from app.models.application.enums import ProceedingId, PublicBodyId
from app.models.application.index import Proceeding, PublicBody


def seed():
    """
    Seeds reference data (proceedings and public bodies) into the database.
    This function is idempotent and safe to run multiple times.
    """
    proceedings = [
        {
            "proceeding_id": "IQ011",
            "proceeding_name": "An individual has died in police custody",
            "proceeding_description": "An individual has died in police custody",
        },
        {
            "proceeding_id": "IQ012",
            "proceeding_name": "An individual has died during police pursuit",
            "proceeding_description": "An individual has died during police pursuit",
        },
        {
            "proceeding_id": "IQ013",
            "proceeding_name": "An individual has died following a police shooting",
            "proceeding_description": "An individual has died following a police shooting",
        },
        {
            "proceeding_id": "IQ014",
            "proceeding_name": "An individual has died in prison",
            "proceeding_description": "An individual has died in prison",
        },
        {
            "proceeding_id": "IQ015",
            "proceeding_name": "An individual has died following release from custody / prison",
            "proceeding_description": "An individual has died following release from custody / prison",
        },
        {
            "proceeding_id": "IQ016",
            "proceeding_name": "An individual has died in a young offender’s institution",
            "proceeding_description": "An individual has died in a young offender’s institution",
        },
        {
            "proceeding_id": "IQ017",
            "proceeding_name": "An individual has died in detention under the Mental Health Act 1983",
            "proceeding_description": "An individual has died in detention under the Mental Health Act 1983",
        },
        {
            "proceeding_id": "IQ018",
            "proceeding_name": "An individual has died during or following medical care or treatment",
            "proceeding_description": "An individual has died during or following medical care or treatment",
        },
        {
            "proceeding_id": "IQ019",
            "proceeding_name": "An individual has died following failure, or alleged failure, to provide medical treatment",
            "proceeding_description": "An individual has died following failure, or alleged failure, to provide medical treatment",
        },
        {
            "proceeding_id": "IQ020",
            "proceeding_name": "An individual has died while receiving mental health care in the community",
            "proceeding_description": "An individual has died while receiving mental health care in the community",
        },
        {
            "proceeding_id": "IQ021",
            "proceeding_name": "An individual has died while receiving care in the community (non-mental health)",
            "proceeding_description": "An individual has died while receiving care in the community (non-mental health)",
        },
        {
            "proceeding_id": "IQ022",
            "proceeding_name": "An individual has died while in supported living",
            "proceeding_description": "An individual has died while in supported living",
        },
        {
            "proceeding_id": "IQ023",
            "proceeding_name": "An individual has died following failure, or alleged failure, to provide care services",
            "proceeding_description": "An individual has died following failure, or alleged failure, to provide care services",
        },
        {
            "proceeding_id": "IQ024",
            "proceeding_name": "An individual has died from alleged safeguarding failures",
            "proceeding_description": "An individual has died from alleged safeguarding failures",
        },
        {
            "proceeding_id": "IQ025",
            "proceeding_name": "A child has died that was subject to a care or interim care order",
            "proceeding_description": "A child has died that was subject to a care or interim care order",
        },
        {
            "proceeding_id": "IQ026",
            "proceeding_name": "A child has died following from failure, or alleged failure, to take a child into care",
            "proceeding_description": "A child has died following from failure, or alleged failure, to take a child into care",
        },
        {
            "proceeding_id": "IQ027",
            "proceeding_name": "A child has died from alleged deliberate abuse of a child in care",
            "proceeding_description": "A child has died from alleged deliberate abuse of a child in care",
        },
        {
            "proceeding_id": "IQ028",
            "proceeding_name": "A child has died by alleged suicide",
            "proceeding_description": "A child has died by alleged suicide",
        },
        {
            "proceeding_id": "IQ029",
            "proceeding_name": "A child has died that was subject to safeguarding concerns",
            "proceeding_description": "A child has died that was subject to safeguarding concerns",
        },
        {
            "proceeding_id": "IQ030",
            "proceeding_name": "A child has died that was referred to social services",
            "proceeding_description": "A child has died that was referred to social services",
        },
        {
            "proceeding_id": "IQ031",
            "proceeding_name": "A child has died with Special Educational Needs and Disabilities (SEND)",
            "proceeding_description": "A child has died with Special Educational Needs and Disabilities (SEND)",
        },
        {
            "proceeding_id": "IQ032",
            "proceeding_name": "An individual has died in an educational setting",
            "proceeding_description": "An individual has died in an educational setting",
        },
        {
            "proceeding_id": "IQ033",
            "proceeding_name": "An individual has died from failures, or alleged failures, of an educational institution",
            "proceeding_description": "An individual has died from failures, or alleged failures, of an educational institution",
        },
        {
            "proceeding_id": "IQ034",
            "proceeding_name": "An individual has died in immigration detention",
            "proceeding_description": "An individual has died in immigration detention",
        },
        {
            "proceeding_id": "IQ035",
            "proceeding_name": "An individual has died that was seeking asylum in the country",
            "proceeding_description": "An individual has died that was seeking asylum in the country",
        },
        {
            "proceeding_id": "IQ036",
            "proceeding_name": "An individual has died from alleged issues with the condition of housing",
            "proceeding_description": "An individual has died from alleged issues with the condition of housing",
        },
        {
            "proceeding_id": "IQ037",
            "proceeding_name": "An individual has died in connection with their lack of housing",
            "proceeding_description": "An individual has died in connection with their lack of housing",
        },
        {
            "proceeding_id": "IQ038",
            "proceeding_name": "An individual has died following the termination of disability benefits",
            "proceeding_description": "An individual has died following the termination of disability benefits",
        },
        {
            "proceeding_id": "IQ039",
            "proceeding_name": "An individual has died following alleged mental health issues while in the military",
            "proceeding_description": "An individual has died following alleged mental health issues while in the military",
        },
        {
            "proceeding_id": "IQ040",
            "proceeding_name": "An individual has died from a road traffic collision",
            "proceeding_description": "An individual has died from a road traffic collision",
        },
        {
            "proceeding_id": "IQ041",
            "proceeding_name": "An individual has died in an incident involving public transport",
            "proceeding_description": "An individual has died in an incident involving public transport",
        },
        {
            "proceeding_id": "IQ042",
            "proceeding_name": "A family member has died (Other)",
            "proceeding_description": "A family member has died (Other)",
        },
    ]

    with CustomSessionLocal() as db_session:
        for proceeding in proceedings:
            values = {
                "proceeding_id": ProceedingId(proceeding["proceeding_id"]),
                "proceeding_name": proceeding["proceeding_name"],
                "proceeding_description": proceeding["proceeding_description"],
                "category_of_law": "INQUESTS",
                "certificate_type": "SUBSTANTIVE",
                "level_of_service": "FULL_REPRESENTATION",
                "matter_type": "INQUESTS",
                "scope_limitation_heading": "FINAL_HEARING",
                "scope_description": "This is the scope description",
                "substantive_cost_limitation": 10000,
            }
            stmt = (
                insert(Proceeding)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=["proceeding_id"],
                    set_={
                        "proceeding_name": proceeding["proceeding_name"],
                        "proceeding_description": proceeding["proceeding_description"],
                        "category_of_law": "INQUESTS",
                        "certificate_type": "SUBSTANTIVE",
                        "level_of_service": "FULL_REPRESENTATION",
                        "matter_type": "INQUESTS",
                        "scope_limitation_heading": "FINAL_HEARING",
                        "scope_description": "This is the scope description",
                        "substantive_cost_limitation": 10000,
                    },
                )
            )
            db_session.exec(stmt)

        for member in PublicBodyId:
            stmt = (
                insert(PublicBody)
                .values(
                    public_body_id=member,
                    public_body_description=member.value,
                )
                .on_conflict_do_nothing(index_elements=["public_body_id"])
            )
            db_session.exec(stmt)

        db_session.commit()


if __name__ == "__main__":
    seed()
