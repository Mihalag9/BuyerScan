from __future__ import annotations

import hashlib
from typing import Any


LAYOUTS = [
    ("diagonal-hero", "Diagonal hero"),
    ("split-spec", "Split spec"),
    ("editorial-poster", "Editorial poster"),
    ("price-stage", "Price stage"),
    ("feature-grid", "Feature grid"),
    ("vertical-band", "Vertical band"),
    ("magazine-crop", "Magazine crop"),
    ("soft-tiles", "Soft tiles"),
    ("tech-ribbon", "Tech ribbon"),
    ("clean-market", "Clean market"),
]

PALETTES = [
    ("graphite-lime", "#111417", "#12d466", "#f6f8f7", "#dfe6e2"),
    ("ink-violet", "#16131f", "#9b38ff", "#fbf8ff", "#e8dcff"),
    ("chalk-teal", "#f6f9f9", "#6b9998", "#1b3030", "#dce9e8"),
    ("rose-cream", "#d89191", "#fff4e8", "#2b2524", "#f4d8d2"),
    ("olive-wood", "#e8e1d2", "#41561f", "#2c241c", "#d1c5a6"),
    ("cocoa-blush", "#4b302a", "#e6a896", "#fff7ef", "#7b4e45"),
    ("ice-blue", "#eef6f8", "#2577a8", "#101820", "#cce6f0"),
    ("mono-yellow", "#151515", "#f4c542", "#fbfaf5", "#e7e0c5"),
    ("mint-black", "#071512", "#34e0a1", "#effbf6", "#bbf2dd"),
    ("terracotta", "#f5e8df", "#bf5d43", "#271b18", "#f0c9ba"),
    ("denim-orange", "#13283a", "#ff9f3f", "#f7fbff", "#c9d9e8"),
    ("sand-plum", "#efe4cf", "#704870", "#241a24", "#ddc8d8"),
    ("silver-blue", "#f1f4f6", "#355c7d", "#111827", "#d7e0e8"),
    ("coral-ink", "#fff1ec", "#e75454", "#17191c", "#ffd2c9"),
    ("aqua-night", "#0e1c24", "#32c7d8", "#f4fbfc", "#c9eef2"),
    ("milk-green", "#fbfaf2", "#7d9b50", "#202316", "#dfe8c8"),
    ("steel-red", "#e9edf0", "#d94343", "#151a1f", "#cbd3d8"),
    ("lavender", "#f4effa", "#7c61bd", "#221c2f", "#ddd0f0"),
    ("coffee-pink", "#ede3d9", "#e798aa", "#332a25", "#d8c9bd"),
    ("white-cobalt", "#ffffff", "#1357d8", "#111827", "#dbe7ff"),
]


def build_templates() -> list[dict[str, Any]]:
    templates: list[dict[str, Any]] = []
    serial = 1
    for layout_index, (layout, layout_name) in enumerate(LAYOUTS):
        for palette_index, (palette_name, bg, accent, ink, soft) in enumerate(PALETTES):
            templates.append(
                {
                    "id": f"tpl-{serial:03d}",
                    "name": f"{layout_name} {palette_index + 1:02d}",
                    "layout": layout,
                    "layout_index": layout_index,
                    "palette_name": palette_name,
                    "bg": bg,
                    "accent": accent,
                    "ink": ink,
                    "soft": soft,
                    "variant": palette_index,
                    "dark": layout_index in {0, 6, 8} or bg.lower() in {"#111417", "#16131f", "#071512", "#0e1c24", "#13283a"},
                }
            )
            serial += 1
    return templates


TEMPLATES = build_templates()


def template_count() -> int:
    return len(TEMPLATES)


def choose_templates(product: str, category: str, seed: str, count: int = 8) -> list[dict[str, Any]]:
    count = max(1, min(count, 24))
    text = f"{product} {category}".lower()
    preferred_layouts: set[str] = set()
    if any(word in text for word in ("mouse", "gaming", "keyboard", "headphone", "electronics", "элект", "мыш")):
        preferred_layouts.update({"diagonal-hero", "tech-ribbon", "vertical-band", "price-stage"})
    if any(word in text for word in ("shoe", "sneaker", "trainer", "footwear", "крос", "обув")):
        preferred_layouts.update({"diagonal-hero", "editorial-poster", "magazine-crop", "clean-market"})
    if any(word in text for word in ("cream", "beauty", "cosmetic", "skincare", "крем", "крас", "космет")):
        preferred_layouts.update({"editorial-poster", "soft-tiles", "feature-grid", "clean-market"})
    if not preferred_layouts:
        preferred_layouts.update({"split-spec", "feature-grid", "soft-tiles", "clean-market"})

    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    offset = int.from_bytes(digest[:4], "big") % len(TEMPLATES)
    ranked = sorted(
        TEMPLATES,
        key=lambda item: (
            0 if item["layout"] in preferred_layouts else 1,
            (item["variant"] - offset) % len(PALETTES),
            item["layout_index"],
        ),
    )

    selected: list[dict[str, Any]] = []
    used_layouts: set[str] = set()
    for item in ranked:
        if item["layout"] in used_layouts and len(used_layouts) < min(count, len(LAYOUTS)):
            continue
        selected.append(item)
        used_layouts.add(item["layout"])
        if len(selected) == count:
            return selected
    for item in ranked:
        if item not in selected:
            selected.append(item)
            if len(selected) == count:
                break
    return selected
