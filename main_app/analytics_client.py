from __future__ import annotations

import asyncio
from typing import Any

import httpx

from settings import settings


class AnalyticsError(RuntimeError):
    pass


async def _create_job(
    client: httpx.AsyncClient, query: str, sample: int, target: int, use_browser: bool
) -> str:
    resp = await client.post(
        f"{settings.analytics_url}/search",
        json={"query": query, "sample": sample, "target": target, "use_browser": use_browser},
    )
    if resp.status_code != 200:
        raise AnalyticsError(f"analytics /search HTTP {resp.status_code}: {resp.text[:200]}")
    job_id = resp.json().get("job_id")
    if not job_id:
        raise AnalyticsError("analytics не вернул job_id")
    return job_id


async def _wait_job(client: httpx.AsyncClient, job_id: str) -> dict[str, Any]:
    loop = asyncio.get_event_loop()
    deadline = loop.time() + settings.analytics_timeout
    last_status = "pending"

    while True:
        if loop.time() > deadline:
            raise AnalyticsError(f"analytics timeout после {settings.analytics_timeout} с")
        resp = await client.get(f"{settings.analytics_url}/search/{job_id}")
        if resp.status_code == 404:
            raise AnalyticsError("job_id не найден на analytics")
        if resp.status_code != 200:
            raise AnalyticsError(f"analytics /search/{{id}} HTTP {resp.status_code}")
        job = resp.json()
        last_status = job.get("status")
        if last_status == "done":
            return job.get("result") or {"products": [], "stats": {}}
        if last_status == "failed":
            raise AnalyticsError(job.get("error") or "analytics job failed")
        await asyncio.sleep(1.0)


async def search_products(
    query: str,
    sample: int = 20,
    target: int = 10,
    use_browser: bool = True,
) -> dict[str, Any]:
    timeout = httpx.Timeout(settings.analytics_timeout + 30, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        job_id = await _create_job(client, query, sample, target, use_browser)
        return await _wait_job(client, job_id)


async def analytics_health() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.analytics_url}/health")
            if resp.status_code == 200:
                return {"ok": True, **resp.json()}
            return {"ok": False, "status": resp.status_code}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}