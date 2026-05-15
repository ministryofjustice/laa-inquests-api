from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, create_engine
from app.config import Config
from app.db.session import CustomSession
from app.models.application.index import Proceeding
from app.models.application.enums import ProceedingId


db_url = f"postgresql://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"

engine = create_engine(db_url, echo=Config.DB_LOGGING)


CustomSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=CustomSession
)


def get_session():
    SQLModel.metadata.create_all(engine)

    proceedings = [
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
    with CustomSessionLocal() as db_session:
        for proceeding in proceedings:
            stmt = (
                insert(Proceeding)
                .values(
                    proceeding_id=ProceedingId(proceeding["proceeding_id"]),
                    proceeding_description=proceeding["proceeding_description"],
                )
                .on_conflict_do_nothing(index_elements=["proceeding_id"])
            )
            db_session.exec(stmt)
        db_session.commit()

        yield db_session
