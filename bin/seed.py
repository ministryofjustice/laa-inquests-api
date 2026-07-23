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
