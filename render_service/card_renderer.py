from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from template_catalog import choose_templates, template_count as _template_count


GENERATED_DIR: Path = Path(__file__).resolve().parent / "generated"
GENERATED_DIR.mkdir(exist_ok=True)

WIN_FONTS: Path = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"


def set_generated_dir(path: Path) -> None:
    global GENERATED_DIR
    GENERATED_DIR = path
    GENERATED_DIR.mkdir(exist_ok=True)


def template_count() -> int:
    return _template_count()


def font(size: int, bold: bool = False, heavy: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "arialbd.ttf" if heavy else None,
        "segoeuib.ttf" if heavy else None,
        "arialbd.ttf" if bold else None,
        "segoeuib.ttf" if bold else None,
        "arial.ttf",
        "segoeui.ttf",
    ]
    for name in candidates:
        if not name:
            continue
        path = WIN_FONTS / name
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def money(value: float | int) -> str:
    return f"{int(round(value)):,}".replace(",", " ") + " ₽"


def dominant_palette(image: Image.Image) -> list[tuple[int, int, int]]:
    sample = image.convert("RGB").resize((120, 120))
    colors = sample.quantize(colors=5).convert("RGB").getcolors(120 * 120)
    if not colors:
        return [(36, 76, 90), (233, 165, 63), (217, 95, 69)]
    colors = sorted(colors, reverse=True)
    return [rgb for _, rgb in colors[:5]]


def contrast(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    r, g, b = rgb
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    return (17, 20, 23) if brightness > 150 else (255, 255, 255)


def fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int,
             min_size: int, heavy: bool = False) -> ImageFont.FreeTypeFont:
    size = start_size
    while size >= min_size:
        fnt = font(size, bold=True, heavy=heavy)
        if draw.textbbox((0, 0), text, font=fnt)[2] <= max_width:
            return fnt
        size -= 2
    return font(min_size, bold=True, heavy=heavy)


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont,
         max_width: int, max_lines: int = 3) -> list[str]:
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=fnt)[2] <= max_width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
            if len(lines) >= max_lines - 1:
                break
    if line and len(lines) < max_lines:
        lines.append(line)
    return lines


def paste_contain(base: Image.Image, product: Image.Image,
                  box: tuple[int, int, int, int], shadow: bool = True) -> None:
    x, y, w, h = box
    product = ImageOps.exif_transpose(product).convert("RGBA")
    product.thumbnail((w, h), Image.LANCZOS)
    px = x + (w - product.width) // 2
    py = y + (h - product.height) // 2
    if shadow:
        alpha = product.getchannel("A")
        shadow_img = Image.new("RGBA", product.size, (0, 0, 0, 125))
        shadow_img.putalpha(alpha.filter(ImageFilter.GaussianBlur(18)))
        base.alpha_composite(shadow_img, (px + 10, py + 24))
    base.alpha_composite(product, (px, py))


def rounded_rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int,
                 fill: tuple[int, int, int, int] | tuple[int, int, int]) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def card_style(product: str, category: str) -> str:
    text = f"{product} {category}".lower()
    if any(w in text for w in ("мыш", "элект", "mouse", "gaming", "headphone", "keyboard", "electronics")):
        return "gaming"
    if any(w in text for w in ("обув", "крос", "sneaker", "shoe", "trainer", "footwear")):
        return "sport"
    if any(w in text for w in ("крас", "крем", "космет", "cream", "beauty", "cosmetic", "skincare")):
        return "beauty"
    return "generic"


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def mix(a: tuple[int, int, int], b: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * amount) for i in range(3))


def with_alpha(color: tuple[int, int, int], alpha: int) -> tuple[int, int, int, int]:
    return color[0], color[1], color[2], alpha


def draw_lines(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], max_width: int,
               max_lines: int, size: int,
               fill: tuple[int, int, int] | tuple[int, int, int, int],
               heavy: bool = False, spacing: int = 6) -> int:
    fnt = fit_text(draw, text, max_width, size, max(20, size - 24), heavy=heavy)
    y = xy[1]
    for line in wrap(draw, text, fnt, max_width, max_lines):
        draw.text((xy[0], y), line, font=fnt, fill=fill)
        y += fnt.size + spacing
    return y


def draw_chip(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str,
              bg: tuple[int, int, int] | tuple[int, int, int, int],
              fg: tuple[int, int, int] | tuple[int, int, int, int], size: int = 24) -> None:
    rounded_rect(draw, box, 22, bg)
    draw.text((box[0] + 20, box[1] + (box[3] - box[1] - size) // 2 - 2),
              text[:34], font=font(size, bold=True), fill=fg)


def draw_feature_stack(draw: ImageDraw.ImageDraw, benefits: list[str], x: int, y: int,
                       width: int, accent: tuple[int, int, int], fg: tuple[int, int, int],
                       muted: tuple[int, int, int], compact: bool = False) -> None:
    row_h = 76 if compact else 92
    for index, item in enumerate((benefits + ["Marketplace ready", "SEO ready"])[:3]):
        top = y + index * row_h
        draw.ellipse((x, top + 8, x + 22, top + 30), fill=accent)
        draw_lines(draw, item, (x + 38, top), width - 42, 2,
                   24 if compact else 28, fg, heavy=True, spacing=2)
        if not compact:
            draw.text((x + 38, top + 46), "WB / Ozon", font=font(18), fill=muted)


def draw_price_block(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], price: str,
                     accent: tuple[int, int, int], fg: tuple[int, int, int]) -> None:
    rounded_rect(draw, box, 30, with_alpha(accent, 235))
    draw.text((box[0] + 28, box[1] + 18), "market avg", font=font(19, bold=True),
              fill=contrast(accent))
    draw.text((box[0] + 28, box[1] + 47), price, font=font(34, bold=True, heavy=True),
              fill=contrast(accent))


def template_colors(template: dict[str, Any]) -> dict[str, tuple[int, int, int]]:
    bg = hex_rgb(template["bg"])
    accent = hex_rgb(template["accent"])
    ink = hex_rgb(template["ink"])
    soft = hex_rgb(template["soft"])
    dark = bool(template.get("dark"))
    return {
        "bg": bg,
        "accent": accent,
        "ink": (248, 250, 252) if dark else ink,
        "muted": (180, 190, 196) if dark else mix(ink, bg, 0.45),
        "soft": soft,
        "panel": (22, 24, 27) if dark else (255, 255, 255),
        "line": (255, 255, 255) if dark else mix(ink, bg, 0.78),
    }


def render_template_card(
    image_path: Path, title: str, product: str, category: str, brand: str,
    benefits: list[str], econ: dict[str, Any], stats: dict[str, Any],
    image_hash: str, template: dict[str, Any],
) -> Path:
    product_img = ImageOps.exif_transpose(Image.open(image_path)).convert("RGBA")
    colors = template_colors(template)
    bg = colors["bg"]
    accent = colors["accent"]
    ink = colors["ink"]
    muted = colors["muted"]
    soft = colors["soft"]
    panel = colors["panel"]
    dark = bool(template.get("dark"))
    layout = template["layout"]
    price = money(stats.get("avg") or econ.get("retail_price") or 0)
    display_title = title.strip() or product.title()
    product_label = product.upper()[:32]

    canvas = Image.new("RGBA", (900, 1200), bg + (255,))
    draw = ImageDraw.Draw(canvas)

    if layout == "diagonal-hero":
        draw.polygon([(650, 0), (900, 0), (900, 1200), (530, 1200)], fill=accent)
        draw.polygon([(0, 0), (710, 0), (530, 1200), (0, 1200)],
                     fill=mix(bg, (0, 0, 0), 0.18) if dark else bg)
        draw.text((68, 54), brand.upper(), font=font(24, bold=True), fill=with_alpha(ink, 210))
        draw.text((68, 148), f"( {category[:20]} )", font=font(34), fill=with_alpha(ink, 220))
        draw_lines(draw, product_label, (68, 208), 520, 2, 78, ink, heavy=True)
        draw_chip(draw, (68, 390, 398, 468), benefits[0],
                  with_alpha((0, 0, 0), 120) if dark else with_alpha((255, 255, 255), 235), ink, 27)
        paste_contain(canvas, product_img, (430, 300, 420, 530))
        draw_feature_stack(draw, benefits[1:], 92, 650, 440, accent, ink, muted)
        draw.text((68, 1120), f"avg price: {price}", font=font(22, bold=True),
                  fill=with_alpha(ink, 220))

    elif layout == "split-spec":
        canvas.paste(mix(bg, (255, 255, 255), 0.08) + (255,), (0, 0, 900, 1200))
        rounded_rect(draw, (54, 54, 478, 1146), 36, soft)
        rounded_rect(draw, (512, 54, 846, 1146), 36, panel)
        paste_contain(canvas, product_img, (92, 190, 350, 680))
        draw.text((92, 86), brand.upper(), font=font(24, bold=True), fill=hex_rgb(template["ink"]))
        draw_lines(draw, display_title, (548, 118), 260, 4, 48, ink, heavy=True)
        draw_price_block(draw, (548, 378, 798, 472), price, accent, ink)
        draw_feature_stack(draw, benefits, 548, 550, 260, accent, ink, muted, compact=True)
        draw.text((548, 1038), f"category: {category[:22]}", font=font(20, bold=True), fill=muted)

    elif layout == "editorial-poster":
        canvas.paste(mix(bg, (255, 255, 255), 0.3) + (255,), (0, 0, 900, 1200))
        draw.rectangle((0, 0, 900, 320), fill=bg)
        draw.text((68, 58), brand.upper(), font=font(24, bold=True), fill=ink)
        draw_lines(draw, product_label, (68, 112), 760, 2, 92, ink, heavy=True)
        rounded_rect(draw, (620, 250, 792, 312), 31, accent)
        draw.text((648, 267), price, font=font(26, bold=True), fill=contrast(accent))
        paste_contain(canvas, product_img, (115, 330, 670, 540), shadow=True)
        for i, item in enumerate(benefits[:3]):
            x = 76 + i * 270
            rounded_rect(draw, (x, 938, x + 226, 1068), 24, with_alpha(panel, 235))
            draw.text((x + 24, 960), f"0{i + 1}", font=font(22, bold=True), fill=accent)
            draw_lines(draw, item, (x + 24, 994), 178, 2, 22, ink, heavy=True)

    elif layout == "price-stage":
        canvas.paste(bg + (255,), (0, 0, 900, 1200))
        draw.ellipse((-220, -260, 540, 500), fill=with_alpha(soft, 220))
        draw.ellipse((560, 660, 1160, 1260), fill=with_alpha(accent, 190))
        draw.text((66, 62), brand.upper(), font=font(24, bold=True), fill=ink)
        draw_lines(draw, display_title, (66, 132), 560, 3, 64, ink, heavy=True)
        rounded_rect(draw, (596, 86, 820, 180), 42, accent)
        draw.text((626, 116), price, font=font(34, bold=True, heavy=True), fill=contrast(accent))
        paste_contain(canvas, product_img, (112, 350, 676, 520), shadow=True)
        rounded_rect(draw, (84, 920, 816, 1088), 38, with_alpha(panel, 238))
        draw_feature_stack(draw, benefits, 120, 952, 620, accent, ink, muted, compact=True)

    elif layout == "feature-grid":
        canvas.paste(mix(bg, (255, 255, 255), 0.15) + (255,), (0, 0, 900, 1200))
        draw.rectangle((0, 0, 900, 160), fill=bg)
        draw.text((66, 54), brand.upper(), font=font(24, bold=True), fill=ink)
        draw.text((640, 54), price, font=font(30, bold=True), fill=ink)
        paste_contain(canvas, product_img, (188, 205, 525, 440), shadow=True)
        draw_lines(draw, product_label, (66, 678), 760, 2, 66, ink, heavy=True)
        boxes = [(66, 832, 398, 1018), (430, 832, 794, 1018), (66, 1040, 794, 1134)]
        for i, box in enumerate(boxes):
            rounded_rect(draw, box, 24, panel)
            draw.text((box[0] + 24, box[1] + 22), benefits[i % len(benefits)],
                      font=font(25, bold=True), fill=ink)
            draw.rectangle((box[0] + 24, box[3] - 34, box[0] + 108, box[3] - 24), fill=accent)

    elif layout == "vertical-band":
        canvas.paste(bg + (255,), (0, 0, 900, 1200))
        draw.rectangle((0, 0, 255, 1200), fill=accent)
        draw.rectangle((255, 0, 270, 1200), fill=with_alpha(soft, 220))
        draw.text((54, 64), brand[:14].upper(), font=font(24, bold=True), fill=contrast(accent))
        draw_lines(draw, product_label, (318, 84), 500, 2, 76, ink, heavy=True)
        paste_contain(canvas, product_img, (226, 318, 610, 500), shadow=True)
        draw_price_block(draw, (54, 908, 312, 1008), price, soft, contrast(accent))
        draw_feature_stack(draw, benefits, 354, 884, 410, accent, ink, muted, compact=True)

    elif layout == "magazine-crop":
        canvas.paste(bg + (255,), (0, 0, 900, 1200))
        paste_contain(canvas, product_img, (60, 250, 780, 680), shadow=True)
        draw.rectangle((0, 0, 900, 238), fill=with_alpha(panel, 235))
        draw.text((64, 54), brand.upper(), font=font(24, bold=True), fill=ink)
        draw_lines(draw, product_label, (64, 98), 720, 2, 72, ink, heavy=True)
        rounded_rect(draw, (72, 900, 828, 1098), 34, with_alpha(panel, 238))
        draw_feature_stack(draw, benefits, 110, 932, 500, accent, ink, muted, compact=True)
        draw.text((646, 992), price, font=font(31, bold=True, heavy=True), fill=accent)

    elif layout == "soft-tiles":
        canvas.paste(mix(bg, (255, 255, 255), 0.25) + (255,), (0, 0, 900, 1200))
        draw.rounded_rectangle((48, 48, 852, 1152), radius=34, fill=panel)
        draw.text((88, 90), brand.upper(), font=font(23, bold=True), fill=muted)
        draw_lines(draw, display_title, (88, 140), 560, 3, 58, ink, heavy=True)
        rounded_rect(draw, (642, 96, 792, 154), 29, accent)
        draw.text((666, 112), price, font=font(24, bold=True), fill=contrast(accent))
        for i, item in enumerate(benefits[:3]):
            x = 88 + i * 238
            rounded_rect(draw, (x, 790, x + 205, 960), 26,
                         soft if i % 2 == 0 else mix(soft, accent, 0.18))
            draw_lines(draw, item, (x + 22, 820), 160, 3, 22,
                       hex_rgb(template["ink"]), heavy=True)
        paste_contain(canvas, product_img, (150, 330, 600, 410), shadow=True)

    elif layout == "tech-ribbon":
        canvas.paste(bg + (255,), (0, 0, 900, 1200))
        for y in range(300, 1220, 170):
            draw.polygon([(0, y), (900, y + 52), (900, y + 84), (0, y + 32)],
                         fill=with_alpha(accent, 22))
        draw.rectangle((64, 64, 836, 1136), outline=with_alpha(accent, 180), width=3)
        draw.text((94, 96), brand.upper(), font=font(24, bold=True), fill=ink)
        draw_lines(draw, product_label, (94, 160), 510, 2, 72, ink, heavy=True)
        paste_contain(canvas, product_img, (350, 305, 450, 520), shadow=True)
        rounded_rect(draw, (76, 688, 540, 1012), 28, with_alpha(panel, 224))
        draw_feature_stack(draw, benefits, 94, 718, 390, accent, ink, muted)
        draw_price_block(draw, (94, 1018, 356, 1110), price, accent, ink)

    else:
        canvas.paste((247, 249, 250, 255), (0, 0, 900, 1200))
        rounded_rect(draw, (56, 56, 844, 1144), 30, (255, 255, 255))
        draw.rectangle((56, 56, 844, 160), fill=soft)
        draw.text((92, 92), brand.upper(), font=font(24, bold=True),
                  fill=hex_rgb(template["ink"]))
        draw.text((642, 92), price, font=font(29, bold=True), fill=accent)
        paste_contain(canvas, product_img, (120, 215, 660, 510), shadow=True)
        draw_lines(draw, display_title, (98, 760), 700, 3, 52,
                   hex_rgb(template["ink"]), heavy=True)
        draw_feature_stack(draw, benefits, 104, 952, 620, accent,
                           hex_rgb(template["ink"]), muted, compact=True)

    output = GENERATED_DIR / f"{image_hash}-{template['id']}.png"
    canvas.convert("RGB").save(output, "PNG", optimize=True)
    return output


def generate_variants(
    image_path: Path, title: str, product: str, category: str, brand: str,
    benefits: list[str], econ: dict[str, Any], stats: dict[str, Any],
    image_hash: str, count: int = 8,
) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    selected = choose_templates(product, category, image_hash, count=count)
    for template in selected:
        path = render_template_card(image_path, title, product, category, brand,
                                    benefits, econ, stats, image_hash, template)
        variants.append({
            "id": template["id"],
            "name": template["name"],
            "layout": template["layout"],
            "palette": template["palette_name"],
            "card_url": f"/generated/{path.name}",
        })
    return variants