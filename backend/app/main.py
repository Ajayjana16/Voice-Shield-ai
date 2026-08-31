from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import Settings, get_settings
from app.db.store import init_db
from app.services.detection.scam_classifier import get_model_bundle


def get_cors_origins(settings: Settings) -> list[str]:
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]
    if settings.frontend_url:
        for url in settings.frontend_url.split(","):
            u = url.strip().rstrip("/")
            if u and u not in origins:
                origins.append(u)
    if settings.allowed_origins:
        for url in settings.allowed_origins.split(","):
            u = url.strip().rstrip("/")
            if u and u not in origins:
                origins.append(u)
    return origins


def create_app() -> FastAPI:
    settings = get_settings()
    init_db()
    # Preload trained NLP scam classification model on startup
    get_model_bundle()

    app = FastAPI(title=settings.app_name, version="0.1.0")
    cors_origins = get_cors_origins(settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix=settings.api_prefix)
    return app


app = create_app()
