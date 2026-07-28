import sys
import os

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
            "proceeding_id": "IQPC",
            "proceeding_name": "Death in police custody",
            "proceeding_description": "Death in police custody",
        },
        {
            "proceeding_id": "IQPO",
            "proceeding_name": "Death in prison",
            "proceeding_description": "Death in prison",
        },
        {
            "proceeding_id": "IQMT",
            "proceeding_name": "Death during medical treatment",
            "proceeding_description": "Death during medical treatment",
        },
        {
            "proceeding_id": "IQMH",
            "proceeding_name": "Death in mental health detention",
            "proceeding_description": "Death in mental health detention",
        },
        {
            "proceeding_id": "IQMC",
            "proceeding_name": "Death relating to mental health care in the community",
            "proceeding_description": "Death relating to mental health care in the community",
        },
        {
            "proceeding_id": "IQCC",
            "proceeding_name": "Death relating to other care in the community",
            "proceeding_description": "Death relating to other care in the community",
        },
        {
            "proceeding_id": "IQHO",
            "proceeding_name": "Death relating to issues with condition/safety of housing",
            "proceeding_description": "Death relating to issues with condition/safety of housing",
        },
        {
            "proceeding_id": "IQCA",
            "proceeding_name": "Death relating to a child’s care arrangements",
            "proceeding_description": "Death relating to a child’s care arrangements",
        },
        {
            "proceeding_id": "IQDV",
            "proceeding_name": "Death relating to failure to prevent domestic violence",
            "proceeding_description": "Death relating to failure to prevent domestic violence",
        },
        {
            "proceeding_id": "IQED",
            "proceeding_name": "Death relating to issues in an educational setting",
            "proceeding_description": "Death relating to issues in an educational setting",
        },
        {
            "proceeding_id": "IQTR",
            "proceeding_name": "Death relating to issues relating to transport",
            "proceeding_description": "Death relating to issues relating to transport",
        },
        {
            "proceeding_id": "IQOT",
            "proceeding_name": "Other",
            "proceeding_description": "Other",
        },
        {
            "proceeding_id": "IQPC",
            "proceeding_name": "Death in police custody",
            "proceeding_description": "Death in police custody",
        },
        {
            "proceeding_id": "IQPO",
            "proceeding_name": "Death in prison",
            "proceeding_description": "Death in prison",
        },
        {
            "proceeding_id": "IQMT",
            "proceeding_name": "Death during medical treatment",
            "proceeding_description": "Death during medical treatment",
        },
        {
            "proceeding_id": "IQMH",
            "proceeding_name": "Death in mental health detention",
            "proceeding_description": "Death in mental health detention",
        },
        {
            "proceeding_id": "IQMC",
            "proceeding_name": "Death relating to mental health care in the community",
            "proceeding_description": "Death relating to mental health care in the community",
        },
        {
            "proceeding_id": "IQCC",
            "proceeding_name": "Death relating to other care in the community",
            "proceeding_description": "Death relating to other care in the community",
        },
        {
            "proceeding_id": "IQHO",
            "proceeding_name": "Death relating to issues with condition/safety of housing",
            "proceeding_description": "Death relating to issues with condition/safety of housing",
        },
        {
            "proceeding_id": "IQCA",
            "proceeding_name": "Death relating to a child’s care arrangements",
            "proceeding_description": "Death relating to a child’s care arrangements",
        },
        {
            "proceeding_id": "IQDV",
            "proceeding_name": "Death relating to failure to prevent domestic violence",
            "proceeding_description": "Death relating to failure to prevent domestic violence",
        },
        {
            "proceeding_id": "IQED",
            "proceeding_name": "Death relating to issues in an educational setting",
            "proceeding_description": "Death relating to issues in an educational setting",
        },
        {
            "proceeding_id": "IQTR",
            "proceeding_name": "Death relating to issues relating to transport",
            "proceeding_description": "Death relating to issues relating to transport",
        },
        {
            "proceeding_id": "IQOT",
            "proceeding_name": "Other",
            "proceeding_description": "Other",
        },
    ]

    public_bodies = [
        "Prime Minister's Office 10 Downing Street",
        "Cabinet Office",
        "Attorney General's Office",
        "Department for Business & Trade",
        "Department for Culture, Media & Sport",
        "Department for Education",
        "Department for Energy Security & Net Zero",
        "Department for Environment, Food & Rural Affairs",
        "Department for Science, Innovation & Technology",
        "Department for Transport",
        "Department for Work & Pensions",
        "Department of Health & Social Care",
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

        for public_body in public_bodies:
            stmt = (
                insert(PublicBody)
                .values(
                    public_body_id=PublicBodyId(public_body),
                    public_body_description=public_body,
                )
                .on_conflict_do_nothing(index_elements=["public_body_id"])
            )
            db_session.exec(stmt)

        db_session.commit()


if __name__ == "__main__":
    seed()
