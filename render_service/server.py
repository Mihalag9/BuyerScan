from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps

import card_renderer
from cutout import ai_status, generate_ai_cutout, segment_product

ROOT = Path(__file__).resolve().parent
UPLOADS = ROOT / "uploads"
GENERATED = ROOT / "generated"
UPLOADS.mkdir(exist_ok=True)
GENERATED.mkdir(exist_ok=True)

card_renderer.set_generated_dir(GENERATED)

PORT = int(os.getenv("RENDER_PORT", "5178"))
MAX_BYTES = 15 * 1024 * 1024
MAX_SIDE = 1600

app = FastAPI(title="TagMaster Render Service")


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()[:24]


def _save_upload(raw: bytes, name: str) -> Path:
    output = UPLOADS / name
    if output.exists():
        return output
    source = Image.open(io.BytesIO(raw))
    source = ImageOps.exif_transpose(source).convert("RGB")
    source.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    source.save(output, "WEBP", quality=85, method=6)
    return output


def _parse_json_list(value: str, fallback: list[str]) -> list[str]:
    if not value:
        return fallback
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass
    return fallback


def _parse_json_dict(value: str) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


@app.post("/render")
async def render(
    image: UploadFile = File(...),
    title: str = Form(""),
    product: str = Form("товар"),
    category: str = Form("маркетплейс"),
    brand: str = Form("NOVA GOODS"),
    benefits: str = Form("[]"),
    retail_price: float = Form(0),
    stats: str = Form("{}"),
    variant_count: int = Form(8),
    do_cutout: bool = Form(True),
):
    raw = await image.read()
    if not raw:
        raise HTTPException(400, "Пустой файл")
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "Файл больше 15 МБ")

    image_hash = _hash(raw)
    image_path = await asyncio.to_thread(_save_upload, raw, f"{image_hash}.webp")

    benefit_list = _parse_json_list(
        benefits, ["Крупный товар", "Понятная выгода", "Готово для WB / Ozon"]
    )
    stat_dict = _parse_json_dict(stats)
    econ = {"retail_price": retail_price}

    cutout_info: dict[str, Any] = {"enabled": False}
    card_source = image_path
    if do_cutout:
        ai_cut = await generate_ai_cutout(image_path, GENERATED, image_hash, product, category)
        cutout_info = ai_cut
        if ai_cut.get("usable") and ai_cut.get("path"):
            card_source = Path(ai_cut["path"])
        else:
            seg = await asyncio.to_thread(segment_product, image_path, GENERATED, image_hash)
            cutout_info = {**cutout_info, "fallback": seg}
            if seg.get("usable") and seg.get("path"):
                card_source = Path(seg["path"])

    variants = await asyncio.to_thread(
        card_renderer.generate_variants,
        card_source,
        title.strip(),
        product.strip(),
        category.strip(),
        brand.strip(),
        benefit_list,
        econ,
        stat_dict,
        image_hash,
        max(1, min(variant_count, 24)),
    )

    return JSONResponse({
        "variants": variants,
        "cutout": cutout_info,
        "template_count": card_renderer.template_count(),
        "image_url": f"/uploads/{image_path.name}",
    })


@app.post("/segment")
async def segment(image: UploadFile = File(...)):
    raw = await image.read()
    if not raw:
        raise HTTPException(400, "Пустой файл")
    image_hash = _hash(raw)
    image_path = await asyncio.to_thread(_save_upload, raw, f"{image_hash}.webp")
    seg = await asyncio.to_thread(segment_product, image_path, GENERATED, image_hash)
    return {"image_url": f"/uploads/{image_path.name}", "segmentation": seg}


@app.get("/ai-status")
async def _ai_status():
    return ai_status()


@app.get("/health")
async def health():
    return {"ok": True, "templates": card_renderer.template_count()}


app.mount("/generated", StaticFiles(directory=str(GENERATED)), name="generated")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS)), name="uploads")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=PORT)