from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import uuid

# pyrefly: ignore [missing-import]
from api.routes import router
from api.auth_routes import router as auth_router

try:
    from config import get_settings
except ImportError:
    from app.config import get_settings

from database.dbconnect import check_connection
from services.redis_cache import RedisCacheService
from logging_config import REQUEST_ID, configure_logging, log_event
from observability.metrics import metrics_registry


# ============================================================
# Application Settings
# ============================================================

settings = get_settings()

configure_logging(
    level=settings.log_level,
    environment=settings.environment,
    log_format=settings.log_format,
)

logger = logging.getLogger("datapilot.app")


# ============================================================
# Application Lifespan
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle.

    This replaces the deprecated FastAPI @app.on_event("startup")
    mechanism.
    """

    # --------------------------------------------------------
    # Startup
    # --------------------------------------------------------

    log_event(
        logger,
        "application_started",
        app_name=settings.app_name,
        app_version=settings.app_version,
        environment=settings.environment,
    )

    yield

    # --------------------------------------------------------
    # Shutdown
    # --------------------------------------------------------

    log_event(
        logger,
        "application_stopped",
        app_name=settings.app_name,
        app_version=settings.app_version,
        environment=settings.environment,
    )


# ============================================================
# FastAPI Application
# ============================================================

app = FastAPI(
    title=settings.app_name,
    description="Natural language interface for database analytics",
    version=settings.app_version,
    lifespan=lifespan,
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# API Routes
# ============================================================

app.include_router(router)
app.include_router(auth_router)


# ============================================================
# Request Logging + HTTP Metrics Middleware
# ============================================================

@app.middleware("http")
async def request_logging_middleware(request, call_next):
    """
    Attach request ID, record request metrics, and emit a safe
    structured completion event.

    The /metrics endpoint is intentionally excluded from HTTP
    request metrics so that polling /metrics does not artificially
    increase the application's request counters and latency data.
    """

    # --------------------------------------------------------
    # Request ID
    # --------------------------------------------------------

    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    token = REQUEST_ID.set(request_id)

    started = time.perf_counter()

    response = None

    # --------------------------------------------------------
    # Exclude /metrics from HTTP request metrics
    # --------------------------------------------------------

    collect_http_metrics = request.url.path != "/metrics"

    if collect_http_metrics:
        metrics_registry.increment("http.requests")

    try:

        # ----------------------------------------------------
        # Execute request
        # ----------------------------------------------------

        response = await call_next(request)

        return response

    except Exception:

        # ----------------------------------------------------
        # Server error
        # ----------------------------------------------------

        if collect_http_metrics:
            metrics_registry.increment("http.server_errors")

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

        # ----------------------------------------------------
        # Request duration
        # ----------------------------------------------------

        duration_ms = (time.perf_counter() - started) * 1000

        if collect_http_metrics:

            metrics_registry.observe(
                "http.request_ms",
                duration_ms,
            )

            # ------------------------------------------------
            # HTTP status classification
            # ------------------------------------------------

            if response is not None:

                status_code = response.status_code

                # 2xx / 3xx
                if 200 <= status_code < 400:

                    metrics_registry.increment(
                        "http.successes"
                    )

                # 4xx
                elif 400 <= status_code < 500:

                    metrics_registry.increment(
                        "http.client_errors"
                    )

                # 5xx
                elif status_code >= 500:

                    metrics_registry.increment(
                        "http.server_errors"
                    )

        # ----------------------------------------------------
        # Structured request completion log
        # ----------------------------------------------------

        if settings.request_logging:

            log_event(
                logger,
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=(
                    response.status_code
                    if response is not None
                    else 500
                ),
                duration_ms=round(duration_ms, 2),
            )

        # ----------------------------------------------------
        # Return request ID to client
        # ----------------------------------------------------

        if response is not None:

            response.headers["X-Request-ID"] = request_id

        # ----------------------------------------------------
        # Reset request context
        # ----------------------------------------------------

        REQUEST_ID.reset(token)


# ============================================================
# Root Endpoint
# ============================================================

@app.get("/")
def root():

    return {
        "message": "Multi-Agent SQL Data Analyst API is running",
        "environment": settings.environment,
    }


# ============================================================
# Health Check
# ============================================================

@app.get("/health")
def health():

    """
    Liveness probe:
    confirms that the application process is running.
    """

    return {
        "status": "healthy",
    }


# ============================================================
# Liveness Probe
# ============================================================

@app.get("/health/live")
def liveness():

    """
    Liveness probe used by orchestrators to detect
    a running process.
    """

    return {
        "status": "alive",
    }


# ============================================================
# Readiness Probe
# ============================================================

@app.get("/health/ready")
def readiness():

    """
    Readiness probe for dependencies required for
    analytical requests.

    PostgreSQL is a hard dependency.

    Redis is intentionally treated as an optional optimization
    because the cache layer gracefully falls back to PostgreSQL
    when Redis is unavailable.
    """

    # --------------------------------------------------------
    # PostgreSQL
    # --------------------------------------------------------

    postgres_healthy = check_connection()

    # --------------------------------------------------------
    # Redis
    # --------------------------------------------------------

    redis_healthy = RedisCacheService().ping()

    # --------------------------------------------------------
    # Build response
    # --------------------------------------------------------

    response = {
        "status": (
            "ready"
            if postgres_healthy
            else "not_ready"
        ),
        "dependencies": {
            "postgres": postgres_healthy,
            "redis": redis_healthy,
        },
    }

    # --------------------------------------------------------
    # PostgreSQL is mandatory
    # --------------------------------------------------------

    if postgres_healthy:

        return response

    return JSONResponse(
        status_code=503,
        content=response,
    )


# ============================================================
# Redis Health
# ============================================================

@app.get("/health/redis")
def redis_health():

    redis_cache = RedisCacheService()

    is_healthy = redis_cache.ping()

    return {
        "status": (
            "healthy"
            if is_healthy
            else "degraded"
        ),
        "redis": is_healthy,
    }


# ============================================================
# Application Metrics
# ============================================================

@app.get("/metrics")
def metrics():

    """
    Return application-level observability metrics.

    This endpoint is excluded from HTTP request metrics
    so that monitoring/polling does not affect the metrics
    being observed.
    """

    return metrics_registry.snapshot()