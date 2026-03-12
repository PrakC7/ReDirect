from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.project_name,
        version="1.0.0",
        description=(
            "Prototype API for adaptive traffic control, emergency corridor requests, "
            "and dashboard-ready signal recommendations."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    def read_root() -> dict[str, str]:
        return {
            "project": settings.project_name,
            "dashboard": f"{settings.api_v1_prefix}/dashboard",
            "docs": "/docs",
        }

    @app.get("/health")
    def root_health_check() -> dict[str, str]:
        return {"status": "healthy"}

    app.include_router(router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
