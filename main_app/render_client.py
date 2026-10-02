from __future__ import annotations

import json
from typing import Any

import httpx

from settings import settings


async def render_cards(
    image_bytes: bytes,
    image_name: str,
    title: str,
    product: str,
    category: str,
    brand: str,
    benefits: list[str],
    retail_price: float,
    stats: dict[str, Any],
    variant_count: int = 8,
    do_cutout: bool = True,
) -> dict[str, Any]:
    files = {"image": (image_name, image_bytes, "image/jpeg")}
    data = {
        "title": title,
        "product": product,
        "category": category,
        "brand": brand,
        "benefits": json.dumps(benefits, ensure_ascii=False),
        "retail_price": str(retail_price or 0),
        "stats": json.dumps(stats or {}, ensure_ascii=False),
        "variant_count": str(variant_count),
        "do_cutout": "true" if do_cutout else "false",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.render_timeout) as client:
            resp = await client.post(f"{settings.render_url}/render", files=files, data=data)
            if resp.status_code != 200:
                return {"variants": [], "error": f"render HTTP {resp.status_code}: {resp.text[:200]}"}
            payload = resp.json()
    except Exception as exc:
        return {"variants": [], "error": str(exc)}

    base = settings.render_url.rstrip("/")
    for variant in payload.get("variants", []):
        url = variant.get("card_url") or ""
        if url and not url.startswith("http"):
            variant["card_url"] = f"{base}{url}"
    return payload