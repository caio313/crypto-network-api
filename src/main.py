from contextlib import asynccontextmanager
from typing import Any
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.api.deps import get_redis_client
from src.api.middleware.auth import get_api_key_tier
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.middleware.auth import AuthMiddleware
from src.api.routes import alerts, gas, networks, transactions
from src.mcp import server as mcp_server
from src.cache.redis import redis_client
from src.core.config import settings
from src.core.logging import structlog
from src.core import metrics

logger = structlog.get_logger()

_beat_process: Any = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    global _beat_process
    
    logger.info("application_starting", environment=settings.environment)
    
    try:
        await redis_client.connect()
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))
    
    try:
        import subprocess
        import sys
        
        beat_proc = subprocess.Popen(
            [sys.executable, "-m", "celery", "-A", "src.ingestion.scheduler", "beat", 
             "--loglevel=info", "--pidfile=/tmp/celerybeat.pid"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _beat_process = beat_proc
        logger.info("celery_beat_started", pid=beat_proc.pid)
    except Exception as e:
        logger.warning("celery_beat_start_failed", error=str(e))
    
    yield
    
    logger.info("application_shutting_down")
    await redis_client.disconnect()
    
    if _beat_process:
        try:
            _beat_process.terminate()
            _beat_process.wait(timeout=5)
            logger.info("celery_beat_stopped")
        except Exception as e:
            logger.warning("celery_beat_stop_failed", error=str(e))


app = FastAPI(
    title="Crypto Network Intelligence API",
    description="AI-first crypto network decision API with native MCP layer",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    redis_status = "connected"
    try:
        if redis_client.client:
            await redis_client.client.ping()
    except Exception:
        redis_status = "disconnected"
    
    return {
        "status": "healthy",
        "environment": settings.environment,
        "redis": redis_status,
    }


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Crypto Network Intelligence API",
        "docs": "/docs",
        "version": "0.1.0",
    }


app.include_router(networks.router)
app.include_router(gas.router)
app.include_router(alerts.router)
app.include_router(transactions.router)
app.include_router(transactions.router_account)
app.include_router(mcp_server.router)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    tier = "unknown"
    try:
        auth_header = request.headers.get("x-api-key")
        if auth_header:
            from src.api.middleware.auth import MOCK_API_KEYS
            tier = MOCK_API_KEYS.get(auth_header, "free")
    except Exception:
        pass
    
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    metrics.track_request_metrics(request, response.status_code, tier)
    metrics.track_latency(request, duration)
    
    return response


@app.get("/metrics")
async def get_metrics():
    return metrics.metrics_endpoint()
