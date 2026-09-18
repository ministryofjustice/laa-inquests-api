from fastapi import APIRouter

router = APIRouter(
    tags=["Monitoring"],
)


@router.get("/health")
def health_check():
    return "Healthy"


@router.get("/status")
def status_check():
    return "OK"
