import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import configure_logging
from app.api.api_v1 import (
    users,
    agents,
    transactions,
    agent_runs,
    demo,
    demo_scenarios,
    config,
    marketplace,
    llm_keys,
)
from app.api.errors import install_exception_handlers
from app.middleware.request_context import RequestContextMiddleware

configure_logging()
logger = logging.getLogger("app.main")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Agent Bank API",
        description="Programmable financial permission layer for AI agents — "
        "give an AI money, but don't give it unlimited control.",
        version="0.2.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    install_exception_handlers(app)

    app.include_router(users.router, prefix=settings.API_V1_STR)
    app.include_router(agents.router, prefix=settings.API_V1_STR)
    app.include_router(transactions.router, prefix=settings.API_V1_STR)
    app.include_router(agent_runs.router, prefix=settings.API_V1_STR)
    app.include_router(demo.router, prefix=settings.API_V1_STR)
    app.include_router(demo_scenarios.router, prefix=settings.API_V1_STR)
    app.include_router(config.router, prefix=settings.API_V1_STR)
    app.include_router(marketplace.router, prefix=settings.API_V1_STR)
    app.include_router(llm_keys.router, prefix=settings.API_V1_STR)

    @app.on_event("startup")
    def on_startup() -> None:
        # Create tables on startup for dev convenience.
        # Production uses: alembic upgrade head
        try:
            from app.db.session import init_db

            init_db()
        except Exception as e:  # pragma: no cover
            logger.error("Failed to initialize database on startup: %s", e)

    @app.get("/")
    async def root():
        return {
            "message": "Welcome to AI Agent Bank API",
            "docs": f"{settings.API_V1_STR}/docs",
        }

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "api_version": "0.2.0"}

    return app


app = create_app()