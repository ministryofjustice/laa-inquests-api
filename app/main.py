from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.routers import applications, security
from app.config.docs import docs_config


def create_app():
    app = FastAPI(**docs_config)

    @app.exception_handler(Exception)
    async def internal_server_exception_handler(request: Request, exc: Exception):
        """Handle uncaught exceptions and return 500 response."""
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred"},
        )

    app.include_router(security)
    app.include_router(applications)

    return app
