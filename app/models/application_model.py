from pydantic import BaseModel


class Application(BaseModel):
    id: str
    status: str
    provider: str
    date_submitted: str
