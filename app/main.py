from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import uuid
# pyrefly: ignore [missing-import]
from api.routes import router

from config import get_settings
from database.dbconnect import check_connection
from services.redis_cache import RedisCacheService
from logging_config import REQUEST_ID, configure_logging, log_event


settings = get_settings()
configure_logging(
    level=settings.log_level,
    environment=settings.environment,
    log_format=settings.log_format,
)
logger = logging.getLogger("datapilot.app")

app = FastAPI(
    title=settings.app_name,
    description="Natural language interface for database analytics",
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.middleware("http")
async def request_logging_middleware(request, call_next):
    """Attach a request ID and emit one safe structured completion event."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = REQUEST_ID.set(request_id)
    started = time.perf_counter()
    response = None

    try:
        response = await call_next(request)
        return response
    except Exception:
        logger.exception(
            "request_failed",
            extra={
                "structured_payload": {
                    "event": "request_failed",
                    "method": request.method,
                    "path": request.url.path,
                    "request_id": request_id,
                }
            },
        )
        raise
    finally:
        duration_ms = (time.perf_counter() - started) * 1000
        if settings.request_logging:
            log_event(
                logger,
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code if response is not None else 500,
                duration_ms=round(duration_ms, 2),
            )
        if response is not None:
            response.headers["X-Request-ID"] = request_id
        REQUEST_ID.reset(token)


@app.on_event("startup")
def startup_log():
    log_event(
        logger,
        "application_started",
        app_name=settings.app_name,
        app_version=settings.app_version,
        environment=settings.environment,
    )


@app.get("/")
def root():
    return {
        "message": "Multi-Agent SQL Data Analyst API is running",
        "environment": settings.environment,
    }


@app.get("/health")
def health():
    """Liveness probe: confirms the application process is running."""
    return {
        "status": "healthy",
    }


@app.get("/health/live")
def liveness():
    """Liveness probe used by orchestrators to detect a running process."""
    return {
        "status": "alive",
    }


@app.get("/health/ready")
def readiness():
    """Readiness probe for dependencies required for analytical requests.

    PostgreSQL is a hard dependency. Redis is intentionally treated as an
    optional optimization because the cache layer gracefully falls back to
    PostgreSQL when Redis is unavailable.
    """
    postgres_healthy = check_connection()
    redis_healthy = RedisCacheService().ping()

    response = {
        "status": "ready" if postgres_healthy else "not_ready",
        "dependencies": {
            "postgres": postgres_healthy,
            "redis": redis_healthy,
        },
    }

    if postgres_healthy:
        return response

    return JSONResponse(status_code=503, content=response)


@app.get("/health/redis")
def redis_health():
    redis_cache = RedisCacheService()
    is_healthy = redis_cache.ping()
    return {
        "status": "healthy" if is_healthy else "degraded",
        "redis": is_healthy,
    }
