"""Подопытный HTTP-сервис для лабы 2: RED-метрики, JSON-логи с trace_id, OTel-трейсы."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "api")
OTLP_ENDPOINT = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "http://jaeger-collector:4318",
)


# --- логирование -----------------------------------------------------------

class JsonFormatter(logging.Formatter):
    """Структурированные JSON-логи со встроенным trace_id."""

    def format(self, record: logging.LogRecord) -> str:
        span = trace.get_current_span()
        ctx = span.get_span_context() if span is not None else None
        trace_id = ""
        span_id = ""
        if ctx is not None and ctx.is_valid:
            trace_id = format(ctx.trace_id, "032x")
            span_id = format(ctx.span_id, "016x")

        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": trace_id,
            "span_id": span_id,
        }
        for key in ("delay_seconds", "n", "ok", "failed"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> logging.Logger:
    LoggingInstrumentor().instrument(set_logging_format=False)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    return logging.getLogger(SERVICE_NAME)


# --- трейсы ----------------------------------------------------------------

def setup_tracing() -> trace.Tracer:
    resource = Resource.create({"service.name": SERVICE_NAME})
    provider = TracerProvider(resource=resource)
    # OTLP/HTTP: экспортер сам допишет /v1/traces к базовому endpoint.
    exporter = OTLPSpanExporter(endpoint=f"{OTLP_ENDPOINT.rstrip('/')}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(SERVICE_NAME)


# --- метрики RED -----------------------------------------------------------

REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
ERRORS = Counter(
    "http_errors_total",
    "Total HTTP 5xx responses",
    ["method", "endpoint"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


# --- приложение ------------------------------------------------------------

logger = setup_logging()
tracer = setup_tracing()
app = FastAPI(title=SERVICE_NAME)
FastAPIInstrumentor.instrument_app(app)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next: Any) -> Response:
    if request.url.path == "/metrics":
        return await call_next(request)

    endpoint = request.url.path
    method = request.method
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        elapsed = time.perf_counter() - started
        REQUESTS.labels(method=method, endpoint=endpoint, status=str(status)).inc()
        LATENCY.labels(method=method, endpoint=endpoint).observe(elapsed)
        if status >= 500:
            ERRORS.labels(method=method, endpoint=endpoint).inc()


@app.get("/health", response_class=PlainTextResponse)
async def health() -> str:
    logger.info("health check")
    return "ok"


@app.get("/fail")
async def fail() -> JSONResponse:
    span = trace.get_current_span()
    span.set_status(Status(StatusCode.ERROR, "intentional failure"))
    span.record_exception(RuntimeError("intentional failure from /fail"))
    logger.error("intentional failure from /fail")
    return JSONResponse(status_code=500, content={"error": "intentional failure"})


@app.get("/slow")
async def slow() -> dict[str, float]:
    delay = random.uniform(1.0, 3.0)
    with tracer.start_as_current_span("slow-op") as span:
        span.set_attribute("slow.delay_seconds", delay)
        logger.info("starting slow operation", extra={"delay_seconds": delay})
        await asyncio.sleep(delay)
    logger.info("slow operation finished", extra={"delay_seconds": delay})
    return {"slept_seconds": round(delay, 3)}


@app.get("/load")
async def load(n: int = 50) -> dict[str, Any]:
    """Пачка внутренних запросов к себе — поднимает RPS для дашборда."""
    n = max(1, min(n, 200))
    base = os.getenv("SELF_BASE_URL", "http://127.0.0.1:8000")
    ok = 0
    failed = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [client.get(f"{base}/health") for _ in range(n)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception) or getattr(r, "status_code", 500) >= 400:
                failed += 1
            else:
                ok += 1
    logger.info("load burst finished", extra={"n": n, "ok": ok, "failed": failed})
    return {"requested": n, "ok": ok, "failed": failed}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
