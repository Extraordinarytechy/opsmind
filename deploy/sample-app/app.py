"""A tiny FastAPI sample workload used to demonstrate the OpsMind loop.

It exposes Prometheus metrics at /metrics and can be pushed into failure on demand
(raised error rate or added latency), so a failure-injection exercise produces a real
SLO breach that OpsMind then diagnoses. This is a lab workload, not a real service.
"""

from __future__ import annotations

import os
import random
import time

from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="opsmind-sample-app")

# Runtime-tunable failure knobs (also settable via env for the initial state).
STATE = {
    "error_rate": float(os.getenv("ERROR_RATE", "0.0")),   # 0..1
    "extra_latency_ms": int(os.getenv("EXTRA_LATENCY_MS", "0")),
}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/work")
def work():
    if STATE["extra_latency_ms"] > 0:
        time.sleep(STATE["extra_latency_ms"] / 1000.0)
    if random.random() < STATE["error_rate"]:
        raise HTTPException(status_code=500, detail="injected failure")
    return {"result": "ok"}


@app.post("/chaos")
def chaos(error_rate: float = 0.0, extra_latency_ms: int = 0):
    """Set the failure knobs (used by scripts/inject_failure.sh)."""
    STATE["error_rate"] = max(0.0, min(1.0, error_rate))
    STATE["extra_latency_ms"] = max(0, extra_latency_ms)
    return {"error_rate": STATE["error_rate"], "extra_latency_ms": STATE["extra_latency_ms"]}


Instrumentator().instrument(app).expose(app)  # /metrics
