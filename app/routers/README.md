# Creating new endpoints
To create new endpoints you need to define the URL route it belongs to and which request method it accepts.

## APIRouter
Each route needs to belong to an APIRouter. APIRouters are analogous to Flask Blueprints in that they group endpoints
together and can be assigned shared a prefix, tags and other attributes.

See [here](https://fastapi.tiangolo.com/reference/apirouter/) for the documentation on the APIRouter class.

```python
from fastapi import APIRouter
from sqlmodel import SQLModel
from app.models.category import Categories

router = APIRouter(prefix="/application", tags=["application"])


@router.get("/{application_id}")
async def read_case(application_id: int):
    # We will discuss how to read from the database below.
    application = {"id": 1, "name": "test", "category": "Housing"}
    return application


class Application(SQLModel):
    name: str  # Pydantic ensures the name is always a string
    category: Categories | None = (
        None  # This means that the category must be of the type Categories or None
    )


@router.post("/")
async def create_application(application: Application):
    return application
```
These create_application route only accepts post requests and requires the request body to be of the form defined by
the Application model.

This means the body needs to contain a name which can be encoded as a string and a category which
matches one of the categories of law defined in the [/app/models/categories.py](../models/category.py) enum class.

To learn more about models please read [/app/models/README.md](../models/README.md)

## Audited report permissions

Every report endpoint uses
[`audit_report_and_require_permission`](./dependencies/report_auditer_permission_checker.py)
with its required permission, the audit use case type and a writer that maps the
request onto that use case. Other routes can pass a different use case and writer
to record a different audit event type:

```python
dependencies = [
    Depends(
        audit_report_and_require_permission(
            possible_permissions=Permission.REPORTS_CLAIM_WORKFLOW_READ,
            audit_use_case_type=ReportAuditUseCase,
            audit_writer=ReportAuditWriter(report_type=ReportType.CLAIMS_BACKLOG),
        )
    )
]
```

Authentication runs first. For authenticated requests, the dependency builds the
audit use case and executes the audit inside its failure handler before
enforcing permission:

| Permission | Audit outcome | Response |
| --- | --- | --- |
| Granted | Success | Report download |
| Denied | Success | 403; audit persisted |
| Granted | Setup, write, or commit failure | 500; no report download |
| Denied | Setup, write, or commit failure | 403; no report download |

Missing or invalid authentication retains the existing authentication response.
The failure handler logs audit errors without including user details or tokens.
Report generation runs only after the dependency succeeds and is outside the
audit failure handler.

## Reading and writing to the database
Database connections are managed with SQLModel sessions, these are inherited from SQLAlchemy sessions.

If your endpoint depends on a database session you can pass this into your routing function using the
FastAPI `Depends()` method.

```python
from fastapi import APIRouter, HTTPException, Depends
from app.models.application import ApplicationRequest, Application
from sqlmodel import Session, select
from app.db import get_session
from datetime import datetime

router = APIRouter(
    prefix="/cases",
    tags=["cases"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{application_id}", tags=["applications"])
async def read_case(application_id: str, session: Session = Depends(get_session)):
    application = session.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="application not found")
    return application


@router.post("/", tags=["applications"], response_model=Application)
def create_application(
    request: applicationRequest, session: Session = Depends(get_session)
):
    application = Application(
        category=request.category, time=datetime.now(), name=request.name, id=1
    )
    session.add(application)
    session.commit()
    session.refresh(application)
    return application
```