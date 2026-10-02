from __future__ import annotations

import base64
import importlib.util
import os
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageFilter, ImageOps

try:
    import numpy as np
except Exception:
    np = None


OPENAI_IMAGES_EDIT_URL = "https://api.openai.com/v1/images/edits"


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def ai_status() -> dict[str, Any]:
    return {
        "segmentation": {
            "provider": os.getenv("SEGMENTATION_PROVIDER", "auto"),
            "rembg_available": _module_available("rembg"),
            "onnxruntime_available": _module_available("onnxruntime"),
            "fallback": "border-color-cutout",
        },
        "image_generation": {
            "provider": os.getenv("IMAGE_GENERATION_PROVIDER", "openai"),
            "enabled": bool(os.getenv("OPENAI_API_KEY")),
            "model": os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1"),
        },
    }


def usable_alpha(path: Path) -> tuple[bool, float]:
    with Image.open(path) as img:
        rgba = img.convert("RGBA")
        alpha = rgba.getchannel("A")
        if np is None:
            hist = alpha.histogram()
            opaque = sum(hist[72:])
            ratio = opaque / max(1, rgba.width * rgba.height)
        else:
            ratio = float((np.array(alpha) > 72).mean())
    return 0.08 <= ratio <= 0.92, ratio


def _simple_cutout(source: Path, output: Path) -> dict[str, Any]:
    image = ImageOps.exif_transpose(Image.open(source)).convert("RGBA")
    image.thumbnail((1200, 1200), Image.LANCZOS)

    if np is None:
        image.save(output, "PNG")
        return {
            "path": str(output),
            "provider": "fallback-original",
            "usable": False,
            "alpha_ratio": 1.0,
            "error": "numpy не установлен",
        }

    arr = np.asarray(image).astype(np.int16)
    rgb = arr[:, :, :3]
    height, width = rgb.shape[:2]
    border_width = max(8, min(width, height) // 28)
    border = np.concatenate(
        [
            rgb[:border_width, :, :].reshape(-1, 3),
            rgb[-border_width:, :, :].reshape(-1, 3),
            rgb[:, :border_width, :].reshape(-1, 3),
            rgb[:, -border_width:, :].reshape(-1, 3),
        ],
        axis=0,
    )
    bg = np.median(border, axis=0)
    distance = np.linalg.norm(rgb - bg, axis=2)
    threshold = max(18.0, float(np.percentile(distance, 58)))
    softness = max(18.0, threshold * 0.55)
    alpha = np.clip((distance - threshold) / softness, 0, 1)
    alpha = (alpha * 255).astype(np.uint8)

    mask = Image.fromarray(alpha, "L")
    mask = mask.filter(ImageFilter.MaxFilter(7))
    mask = mask.filter(ImageFilter.GaussianBlur(2.4))
    out = image.copy()
    out.putalpha(mask)
    out.save(output, "PNG", optimize=True)

    ok, ratio = usable_alpha(output)
    return {
        "path": str(output),
        "provider": "fallback-border-color",
        "usable": ok,
        "alpha_ratio": round(ratio, 4),
    }


def segment_product(source: Path, output_dir: Path, image_hash: str) -> dict[str, Any]:
    output = output_dir / f"{image_hash}-cutout.png"
    provider = os.getenv("SEGMENTATION_PROVIDER", "auto").lower()

    if output.exists():
        ok, ratio = usable_alpha(output)
        return {
            "path": str(output),
            "provider": "cached",
            "usable": ok,
            "alpha_ratio": round(ratio, 4),
        }

    if provider in {"auto", "rembg"} and _module_available("rembg"):
        try:
            from rembg import remove

            result = remove(source.read_bytes())
            output.write_bytes(result)
            ok, ratio = usable_alpha(output)
            return {
                "path": str(output),
                "provider": "rembg",
                "usable": ok,
                "alpha_ratio": round(ratio, 4),
            }
        except Exception as exc:
            fallback = _simple_cutout(source, output)
            fallback["error"] = f"rembg: {exc}"
            return fallback

    return _simple_cutout(source, output)


def _data_url(path: Path) -> str:
    mime = "image/png"
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    elif suffix == ".webp":
        mime = "image/webp"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _decode_image_response(payload: dict[str, Any], output: Path) -> bool:
    data = payload.get("data") or []
    if not data:
        return False
    encoded = data[0].get("b64_json")
    if not encoded:
        return False
    output.write_bytes(base64.b64decode(encoded))
    return True


async def generate_ai_cutout(
    source: Path, output_dir: Path, image_hash: str, product: str, category: str
) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    provider = os.getenv("IMAGE_GENERATION_PROVIDER", "openai").lower()
    if provider not in {"openai", "gpt-image"} or not api_key:
        return {"enabled": False, "provider": provider, "reason": "OPENAI_API_KEY не задан"}

    output = output_dir / f"{image_hash}-ai-cutout.png"
    if output.exists():
        ok, ratio = usable_alpha(output)
        return {
            "enabled": True,
            "path": str(output),
            "provider": "openai-cached",
            "usable": ok,
            "alpha_ratio": round(ratio, 4),
        }

    prompt = (
        "Create a clean marketplace product cutout from the input photo. "
        "Preserve the exact product shape, colors, texture, brand marks, and proportions. "
        "Remove the background completely. Do not add text, labels, hands, props, shadows, "
        "extra products, watermarks, logos, or packaging that is not already visible. "
        f"Product hint: {product}. Category hint: {category}."
    )
    payload = {
        "model": os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1"),
        "images": [{"image_url": _data_url(source)}],
        "prompt": prompt,
        "background": "transparent",
        "input_fidelity": "high",
        "n": 1,
        "output_format": "png",
        "quality": os.getenv("OPENAI_IMAGE_QUALITY", "medium"),
        "size": os.getenv("OPENAI_IMAGE_SIZE", "1024x1024"),
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(OPENAI_IMAGES_EDIT_URL, headers=headers, json=payload)
            response.raise_for_status()
        if not _decode_image_response(response.json(), output):
            return {"enabled": True, "provider": "openai", "usable": False,
                    "error": "в ответе нет b64_json"}
        ok, ratio = usable_alpha(output)
        return {
            "enabled": True,
            "path": str(output),
            "provider": "openai",
            "usable": ok,
            "alpha_ratio": round(ratio, 4),
        }
    except Exception as exc:
        return {"enabled": True, "provider": "openai", "usable": False, "error": str(exc)}