from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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

    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    assets_dir = frontend_dist / "assets"

    if frontend_dist.exists() and assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="preview-assets")

        @app.get("/preview", include_in_schema=False)
        def preview_app() -> FileResponse:
            return FileResponse(frontend_dist / "index.html")

    return app


app = create_app()
