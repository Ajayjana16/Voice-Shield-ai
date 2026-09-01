import logging
import os
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import router
from app.core.config import Settings, get_settings
from app.db.store import init_db
from app.services.detection.scam_classifier import get_model_bundle
from app.services.stt.transcriber import preload_and_warmup_stt

logger = logging.getLogger("voiceshield.memory")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def get_current_memory_mb() -> float:
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return round(process.memory_info().rss / (1024 * 1024), 2)
    except Exception:
        return 0.0


class MemoryAndLatencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        mem_before = get_current_memory_mb()
        t0 = time.perf_counter()
        
        response = await call_next(request)
        
        duration_ms = (time.perf_counter() - t0) * 1000
        mem_after = get_current_memory_mb()
        
        # Log telemetry for endpoints (especially audio analysis and transcription)
        if not request.url.path.endswith(("/live", "/ws/live")):
            logger.info(
                f"[MEM] {request.method} {request.url.path} -> {response.status_code} | "
                f"RAM: {mem_after:.1f}MB (delta: {mem_after - mem_before:+.1f}MB) | Time: {duration_ms:.1f}ms"
            )
        return response


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
    
    # Log baseline memory before loading models
    logger.info(f"Backend initializing. Baseline RAM: {get_current_memory_mb():.1f}MB")
    
    # Preload trained NLP scam classification model on startup (lightweight, ~17MB)
    get_model_bundle()
    logger.info(f"After loading NLP model. Current RAM: {get_current_memory_mb():.1f}MB")

    # Warm up faster-whisper STT singleton (single thread, ~90MB)
    preload_and_warmup_stt()
    logger.info(f"After warming STT model. Total Startup RAM: {get_current_memory_mb():.1f}MB")

    app = FastAPI(title=settings.app_name, version="0.1.0")
    cors_origins = get_cors_origins(settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=r"https://.*(\.vercel\.app|\.onrender\.com)",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add memory and latency telemetry middleware
    app.add_middleware(MemoryAndLatencyMiddleware)

    # ─────────────────────────────────────────────────────────────────────
    # Root-level lightweight probes (Never load heavy models here)
    # ─────────────────────────────────────────────────────────────────────
    @app.get("/", include_in_schema=False)
    @app.head("/", include_in_schema=False)
    def root_probe() -> dict:
        return {
            "status": "online",
            "service": "Voice Shield AI API",
            "memory_rss_mb": get_current_memory_mb(),
        }

    # Mount API routes with /api prefix (e.g. /api/audio/analyze, /api/analyses, /api/health)
    app.include_router(router, prefix=settings.api_prefix)

    # Mount API routes at root level as well (e.g. /audio/analyze, /analyses, /health, /ws/live)
    app.include_router(router, prefix="")

    return app


app = create_app()
