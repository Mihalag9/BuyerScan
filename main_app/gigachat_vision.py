from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from gigachat import GigaChat

from settings import settings

SYSTEM_PROMPT = """\
Ты — экспертный ассистент для продавцов маркетплейсов (Wildberries, Ozon).
Пользователь присылает фотографию товара. Твоя задача — распознать товар и вернуть
строго JSON-объект без markdown-обёртки и без пояснений, со следующими полями:

{
  "product": "короткое название товара в именительном падеже, единственном числе",
  "category": "категория в терминах маркетплейса",
  "search_query": "поисковый запрос для Wildberries, 2-4 слова",
  "title": "продающий заголовок для карточки, до 60 символов, на русском",
  "description": "описание товара для карточки, 2-3 предложения на русском",
  "benefits": ["преимущество 1", "преимущество 2", "преимущество 3"],
  "keywords": ["ключевое слово 1", "ключевое слово 2", "ключевое слово 3"],
  "confidence": 0.95
}

Правила:
- Если на фото несколько товаров — опиши главный по площади.
- Если товар неочевиден — уверенность confidence ставь ниже 0.5, но поля заполни.
- Не выдумывай бренды, состав, размеры и характеристики, которых не видно на фото.
- Название (product) — в нижнем регистре, одно-два слова.
- benefits — ровно 3 элемента, если меньше — дополни нейтральными.
- keywords — 5-8 релевантных поисковых фраз.

Отвечай ТОЛЬКО JSON.
"""


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"GigaChat не вернул JSON. Ответ: {text[:300]}")
    return json.loads(match.group(0))


def _normalize(data: dict[str, Any]) -> dict[str, Any]:
    product = str(data.get("product") or "товар").strip().lower()
    category = str(data.get("category") or "маркетплейс").strip().lower()

    benefits = data.get("benefits") or []
    if not isinstance(benefits, list):
        benefits = [str(benefits)]
    benefits = [str(b).strip() for b in benefits if str(b).strip()][:3]
    while len(benefits) < 3:
        benefits.append("Качественный материал")

    keywords = data.get("keywords") or []
    if not isinstance(keywords, list):
        keywords = [str(keywords)]
    keywords = [str(k).strip() for k in keywords if str(k).strip()][:8]

    try:
        confidence = float(data.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5

    return {
        "product": product,
        "category": category,
        "search_query": str(data.get("search_query") or product).strip(),
        "title": str(data.get("title") or product.title()).strip(),
        "description": str(data.get("description") or "").strip(),
        "benefits": benefits,
        "keywords": keywords,
        "confidence": max(0.0, min(1.0, confidence)),
    }


class GigaChatVision:
    def __init__(self) -> None:
        settings.validate()
        self._client = GigaChat(
            credentials=settings.gigachat_credentials,
            scope=settings.gigachat_scope,
            model=settings.gigachat_model,
            verify_ssl_certs=settings.gigachat_verify_ssl,
        )

    def analyze(self, image_path: Path) -> dict[str, Any]:
        with image_path.open("rb") as fh:
            uploaded = self._client.upload_file(fh, purpose="general")

        data = uploaded.model_dump() if hasattr(uploaded, "model_dump") else vars(uploaded)
        file_id = data.get("id") or data.get("id_")
        if not file_id:
            raise RuntimeError(
                f"GigaChat upload_file вернул неожиданную структуру: {data}"
            )

        payload = {
            "model": settings.gigachat_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": "Распознай товар на фото.",
                    "attachments": [file_id],
                },
            ],
            "temperature": 0.15,
            "max_tokens": 800,
        }

        response = self._client.chat(payload)
        text = response.choices[0].message.content
        return _normalize(_extract_json(text))

        response = self._client.chat(payload)
        text = response.choices[0].message.content
        return _normalize(_extract_json(text))

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass


_vision: GigaChatVision | None = None


def get_vision() -> GigaChatVision:
    global _vision
    if _vision is None:
        _vision = GigaChatVision()
    return _vision