from pydantic import BaseModel
from sqlalchemy import Date


class Application(BaseModel):
    id: str
    status: str
    provider: str
    date_submitted: str