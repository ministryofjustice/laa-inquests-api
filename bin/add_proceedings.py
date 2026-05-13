import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db import get_session
from app.models.application.index import Proceeding, ProceedingId


def add_proceedings(proceeding_list_dict: list[dict]):
    """
    This function creates new proceedings in the spun up local database

    Args:
        proceeding_list_dict: Should contain a list with a dictionary inside
        proceeding ids and plain text descriptions for proceedings
    """
    with next(get_session()) as session:
        for proceeding_info in proceeding_list_dict:
            proceeding_id = proceeding_info.get("proceeding_id")
            proceeding_description = proceeding_info.get("proceeding_description")
            proceeding_to_add = Proceeding(
                proceeding_id=ProceedingId(proceeding_id),
                proceeding_description=proceeding_description,
            )
            session.add(proceeding_to_add)
        session.commit()


proceedings_to_add = [
    {
        "proceeding_id": "PC049",
        "proceeding_description": "CAPA",
    },
    {
        "proceeding_id": "MN035",
        "proceeding_description": "Clinical Negligence",
    },
    {
        "proceeding_id": "MN036",
        "proceeding_description": "Death in Custody - Clinical Negligence",
    },
    {
        "proceeding_id": "MH028",
        "proceeding_description": "Mental Health",
    },
    {
        "proceeding_id": "MH030",
        "proceeding_description": "Death in Detention - Mental Health",
    },
    {
        "proceeding_id": "IQ001",
        "proceeding_description": "Death in Custody",
    },
    {
        "proceeding_id": "IQ002",
        "proceeding_description": "Inquest",
    },
    {
        "proceeding_id": "IQ003",
        "proceeding_description": "Schedule 6 Town & Country Planning Act 1990",
    },
    {
        "proceeding_id": "IQ004",
        "proceeding_description": "Public Inquiry s1 Inquiries Act 2005",
    },
    {
        "proceeding_id": "IQ010",
        "proceeding_description": "S13 Coroner’s Act 1988 - Public Law",
    },
]

add_proceedings(proceedings_to_add)
