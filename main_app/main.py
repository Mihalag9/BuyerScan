from __future__ import annotations

import asyncio
import io
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps

from analytics_client import AnalyticsError, analytics_health, search_products
from gigachat_vision import get_vision
from render_client import render_cards
from settings import ROOT, settings

UPLOADS = ROOT / "uploads"
UPLOADS.mkdir(exist_ok=True)
STATIC = ROOT / "static"

MAX_SIDE = 1600
MAX_BYTES = 15 * 1024 * 1024

app = FastAPI(title="TagMaster Main Service")


def _save_upload(raw: bytes) -> Path:
    path = UPLOADS / f"{uuid.uuid4().hex}.jpg"
    image = Image.open(io.BytesIO(raw))
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    image.save(path, "JPEG", quality=88, optimize=True)
    return path


async def _read_image(image: UploadFile) -> bytes:
    raw = await image.read()
    if not raw:
        raise HTTPException(400, "Пустой файл")
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "Файл больше 15 МБ")
    return raw


async def _detect_sync(image_path: Path) -> dict[str, Any]:
    return await asyncio.to_thread(get_vision().analyze, image_path)


async def _run_analytics(
    query: str,
    sample: int,
    target: int,
    use_browser: bool,
) -> dict[str, Any]:
    if not query:
        return {"products": [], "stats": {}, "error": "пустой search_query"}
    try:
        res = await search_products(
            query,
            sample=max(1, min(sample, 60)),
            target=max(1, min(target, 60)),
            use_browser=use_browser,
        )
        return {
            "products": res.get("products", []),
            "stats": res.get("stats", {}),
            "error": None,
        }
    except AnalyticsError as exc:
        return {"products": [], "stats": {}, "error": str(exc)}
    except Exception as exc:
        return {"products": [], "stats": {}, "error": f"analytics: {exc}"}


async def _run_render(
    raw: bytes,
    detect: dict[str, Any],
    purchase_price: float,
    variant_count: int,
    do_cutout: bool,
) -> dict[str, Any]:
    retail = float(detect.get("retail_price") or 0)
    if retail <= 0:
        retail = max(999.0, purchase_price * 2.2)

    return await render_cards(
        image_bytes=raw,
        image_name="photo.jpg",
        title=detect.get("title") or "",
        product=detect.get("product") or "товар",
        category=detect.get("category") or "маркетплейс",
        brand=detect.get("brand") or "",
        benefits=detect.get("benefits") or [],
        retail_price=retail,
        stats={},
        variant_count=max(1, min(variant_count, 24)),
        do_cutout=do_cutout,
    )


@app.post("/detect")
async def detect(image: UploadFile = File(...)):
    raw = await _read_image(image)
    path = _save_upload(raw)
    try:
        result = await _detect_sync(path)
    except Exception as exc:
        raise HTTPException(500, f"GigaChat: {exc}") from exc
    result["image_url"] = f"/uploads/{path.name}"
    return JSONResponse(result)


@app.post("/render")
async def render(
    image: UploadFile = File(...),
    title: str = Form(""),
    product: str = Form("товар"),
    category: str = Form("маркетплейс"),
    brand: str = Form(""),
    benefits: str = Form("[]"),
    retail_price: float = Form(0),
    variant_count: int = Form(8),
    do_cutout: bool = Form(True),
):
    raw = await _read_image(image)
    path = _save_upload(raw)

    try:
        detect_result = await _detect_sync(path)
    except Exception as exc:
        raise HTTPException(500, f"GigaChat: {exc}") from exc

    if title:
        detect_result["title"] = title
    if product:
        detect_result["product"] = product
    if category:
        detect_result["category"] = category
    if brand:
        detect_result["brand"] = brand
    if benefits and benefits != "[]":
        try:
            import json as _json
            parsed = _json.loads(benefits)
            if isinstance(parsed, list):
                detect_result["benefits"] = [str(x) for x in parsed if str(x).strip()]
        except Exception:
            pass

    cards = await _run_render(raw, detect_result, retail_price, variant_count, do_cutout)
    return JSONResponse(cards)


@app.post("/analyze")
async def analyze(
    image: UploadFile = File(...),
    sample: int = Form(20),
    target: int = Form(10),
    use_browser: bool = Form(True),
    purchase_price: float = Form(0),
    variant_count: int = Form(8),
    do_cutout: bool = Form(True),
):
    raw = await _read_image(image)
    path = _save_upload(raw)

    try:
        detect_result = await _detect_sync(path)
    except Exception as exc:
        raise HTTPException(500, f"GigaChat: {exc}") from exc
    detect_result["image_url"] = f"/uploads/{path.name}"

    query = detect_result.get("search_query") or detect_result.get("product") or ""

    analytics_coro = _run_analytics(query, sample, target, use_browser)
    render_coro = _run_render(raw, detect_result, purchase_price, variant_count, do_cutout)

    market, cards = await asyncio.gather(
        analytics_coro, render_coro, return_exceptions=True
    )

    if isinstance(market, Exception):
        market = {"products": [], "stats": {}, "error": str(market)}
    if isinstance(cards, Exception):
        cards = {"variants": [], "error": str(cards)}

    return JSONResponse({
        "detect": detect_result,
        "market": market,
        "cards": cards,
        "search_query": query,
    })


@app.get("/health")
async def health():
    analytics = await analytics_health()
    return {
        "ok": True,
        "model": settings.gigachat_model,
        "analytics": analytics,
        "render_url": settings.render_url,
        "analytics_url": settings.analytics_url,
    }


app.mount("/uploads", StaticFiles(directory=str(UPLOADS)), name="uploads")
app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=settings.port)