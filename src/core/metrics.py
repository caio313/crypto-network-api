from collections import defaultdict
from functools import wraps

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, Request, Response

from src.core.logging import structlog

logger = structlog.get_logger()


REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "tier", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

NETWORK_SCORE_GAUGE = Gauge(
    "network_score",
    "Current network score",
    ["network"],
)

ALERTS_ACTIVE = Counter(
    "alerts_active_total",
    "Total active alerts by severity",
    ["network", "severity", "alert_type"],
)

CELERY_TASK_COUNT = Counter(
    "celery_tasks_total",
    "Total Celery task executions",
    ["task_name", "status"],
)

CELERY_TASK_DURATION = Histogram(
    "celery_task_duration_seconds",
    "Celery task duration in seconds",
    ["task_name"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
)


def track_request_metrics(request: Request, response_status_code: int, tier: str = "unknown"):
    endpoint = request.url.path
    method = request.method
    
    REQUEST_COUNT.labels(
        method=method,
        endpoint=endpoint,
        tier=tier,
        status_code=response_status_code,
    ).inc()


def track_latency(request: Request, duration: float):
    endpoint = request.url.path
    method = request.method
    
    REQUEST_LATENCY.labels(
        method=method,
        endpoint=endpoint,
    ).observe(duration)


def update_network_score(network: str, score: float):
    NETWORK_SCORE_GAUGE.labels(network=network).set(score)


def increment_alert_counter(network: str, severity: str, alert_type: str):
    ALERTS_ACTIVE.labels(
        network=network,
        severity=severity,
        alert_type=alert_type,
    ).inc()


def track_celery_task(task_name: str, status: str):
    CELERY_TASK_COUNT.labels(task_name=task_name, status=status).inc()


def track_celery_duration(task_name: str, duration: float):
    CELERY_TASK_DURATION.labels(task_name=task_name).observe(duration)


class PrometheusMiddleware:
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        await self.app(scope, receive, send)


def metrics_endpoint() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
