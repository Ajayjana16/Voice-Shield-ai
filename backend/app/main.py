from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.db.store import init_db
from app.services.detection.scam_classifier import get_model_bundle


def create_app() -> FastAPI:
    settings = get_settings()
    init_db()
    # Preload trained NLP scam classification model on startup
    get_model_bundle()

    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix=settings.api_prefix)
    return app


app = create_app()
