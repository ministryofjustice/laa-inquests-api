from fastapi import FastAPI
from app.routers import applications, security
from app.config.docs import docs_config


def create_app():
    app = FastAPI(**docs_config)
    app.include_router(security)
    app.include_router(applications)

    return app
