from __future__ import annotations

import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from wb_client import search, set_progress


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
STATIC.mkdir(exist_ok=True)

PORT = int(os.getenv("ANALYTICS_PORT", "5177"))
MAX_JOBS = 200
JOB_TTL = 3600
MAX_PROGRESS_LINES = 500

app = FastAPI(title="TagMaster Analytics")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="wb-job")
_current = threading.local()


def _on_progress(message: str) -> None:
    job_id = getattr(_current, "id", None)
    if not job_id:
        return
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        if len(job["progress"]) < MAX_PROGRESS_LINES:
            job["progress"].append(
                {"t": round(time.time() - job["started_at"], 2), "message": message}
            )


set_progress(_on_progress)


def _cleanup_old_jobs() -> None:
    now = time.time()
    with _jobs_lock:
        stale = [jid for jid, j in _jobs.items() if now - j["created_at"] > JOB_TTL]
        for jid in stale:
            _jobs.pop(jid, None)
        if len(_jobs) > MAX_JOBS:
            ordered = sorted(_jobs.items(), key=lambda kv: kv[1]["created_at"])
            for jid, _ in ordered[: len(_jobs) - MAX_JOBS]:
                _jobs.pop(jid, None)


def _stats(products: list[dict]) -> dict[str, Any]:
    prices = sorted(
        p["price"] for p in products
        if isinstance(p.get("price"), (int, float)) and p["price"] > 0
    )
    if not prices:
        return {"min": 0, "avg": 0, "max": 0, "median": 0, "count": 0}
    return {
        "min": prices[0],
        "avg": round(sum(prices) / len(prices)),
        "max": prices[-1],
        "median": prices[len(prices) // 2],
        "count": len(prices),
    }


def _run_job(job_id: str, query: str, sample: int, target: int, use_browser: bool) -> None:
    _current.id = job_id
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job["status"] = "running"
        job["started_at"] = time.time()

    try:
        products = search(query, sample=sample, target=target, use_browser=use_browser)
        with _jobs_lock:
            job = _jobs.get(job_id)
            if job is None:
                return
            job["status"] = "done"
            job["result"] = {"products": products, "stats": _stats(products)}
    except Exception as exc:
        with _jobs_lock:
            job = _jobs.get(job_id)
            if job is None:
                return
            job["status"] = "failed"
            job["error"] = str(exc)
    finally:
        with _jobs_lock:
            job = _jobs.get(job_id)
            if job is not None:
                job["finished_at"] = time.time()
                job["elapsed_ms"] = int((job["finished_at"] - job["started_at"]) * 1000)
        _current.id = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    sample: int = Field(20, ge=1, le=60)
    target: int = Field(10, ge=1, le=60)
    use_browser: bool = True


class SearchResponse(BaseModel):
    job_id: str
    status: str


@app.post("/search", response_model=SearchResponse)
async def create_search(req: SearchRequest) -> SearchResponse:
    _cleanup_old_jobs()
    job_id = uuid.uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "query": req.query,
            "sample": req.sample,
            "target": req.target,
            "use_browser": req.use_browser,
            "progress": [],
            "result": None,
            "error": None,
            "created_at": time.time(),
            "started_at": None,
            "finished_at": None,
            "elapsed_ms": None,
        }
    _pool.submit(_run_job, job_id, req.query, req.sample, req.target, req.use_browser)
    return SearchResponse(job_id=job_id, status="pending")


@app.get("/search/{job_id}")
async def get_search(job_id: str) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "job not found")
        return dict(job)


@app.get("/jobs")
async def list_jobs() -> dict[str, Any]:
    with _jobs_lock:
        jobs = [
            {
                "job_id": j["job_id"],
                "status": j["status"],
                "query": j["query"],
                "created_at": j["created_at"],
                "elapsed_ms": j.get("elapsed_ms"),
            }
            for j in _jobs.values()
        ]
    return {"jobs": sorted(jobs, key=lambda j: j["created_at"], reverse=True)}


@app.get("/health")
async def health() -> dict[str, Any]:
    with _jobs_lock:
        active = sum(1 for j in _jobs.values() if j["status"] in {"pending", "running"})
    return {"ok": True, "active_jobs": active}


app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=PORT)