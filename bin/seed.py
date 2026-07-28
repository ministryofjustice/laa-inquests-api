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
            "proceeding_id": "PC049",
            "proceeding_name": "CAPA",
            "proceeding_description": "CAPA",
        },
        {
            "proceeding_id": "MN035",
            "proceeding_name": "Clinical Negligence",
            "proceeding_description": "Clinical Negligence",
        },
        {
            "proceeding_id": "MN036",
            "proceeding_name": "Death in Custody - Clinical Negligence",
            "proceeding_description": "Death in Custody - Clinical Negligence",
        },
        {
            "proceeding_id": "MH028",
            "proceeding_name": "Mental Health",
            "proceeding_description": "Mental Health",
        },
        {
            "proceeding_id": "MH030",
            "proceeding_name": "Death in Detention - Mental Health",
            "proceeding_description": "Death in Detention - Mental Health",
        },
        {
            "proceeding_id": "IQ001",
            "proceeding_name": "Death in Custody",
            "proceeding_description": "Death in Custody",
        },
        {
            "proceeding_id": "IQ002",
            "proceeding_name": "Inquest",
            "proceeding_description": "Inquest",
        },
        {
            "proceeding_id": "IQ003",
            "proceeding_name": "Schedule 6 Town & Country Planning Act 1990",
            "proceeding_description": "Schedule 6 Town & Country Planning Act 1990",
        },
        {
            "proceeding_id": "IQ004",
            "proceeding_name": "Public Inquiry s1 Inquiries Act 2005",
            "proceeding_description": "Public Inquiry s1 Inquiries Act 2005",
        },
        {
            "proceeding_id": "IQ010",
            "proceeding_name": "S13 Coroner's Act 1988 - Public Law",
            "proceeding_description": "S13 Coroner's Act 1988 - Public Law",
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

    with CustomSessionLocal() as db_session:
        for proceeding in proceedings:
            stmt = (
                insert(Proceeding)
                .values(
                    proceeding_id=ProceedingId(proceeding["proceeding_id"]),
                    proceeding_name=proceeding["proceeding_name"],
                    proceeding_description=proceeding["proceeding_description"],
                )
                .on_conflict_do_nothing(index_elements=["proceeding_id"])
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
