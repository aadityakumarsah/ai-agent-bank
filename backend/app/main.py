import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    auth,
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
    app.include_router(auth.router, prefix=settings.API_V1_STR)

    @app.on_event("startup")
    def on_startup() -> None:
        # Fail fast when a production deployment is misconfigured (never start
        # a real-money service that silently degraded to demo/sqlite).
        settings.verify_production_config()

        # Create tables on startup for dev convenience. Production uses
        # `alembic upgrade head` and never auto-creates tables here.
        if settings.is_production:
            return
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

    @app.get("/health/live")
    async def liveness():
        return {"status": "alive", "api_version": "0.2.0"}

    @app.get("/health/ready")
    async def readiness():
        """Readiness probe: verifies the database is reachable too."""
        from sqlalchemy import text

        try:
            from app.db.session import engine

            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as e:  # noqa: BLE001
            logger.error("readiness probe failed: %s", e)
            return JSONResponse(status_code=503, content={"status": "not_ready", "database": "unreachable"})
        return {"status": "ready", "database": "ok"}

    return app


app = create_app()