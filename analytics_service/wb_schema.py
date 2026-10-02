"""Схема: разбор входных запросов и запись результата.

Вход — JSON-массив, у элемента четыре поля:

    {"name": "чехол для iphone 15", "cost": 120.5, "sample": 20, "target": 10}

    name   — название для поиска (обязательно)
    cost   — себестоимость, руб. (обязательно)
    sample — сколько карточек взять со страницы поиска (необязательно, 20)
    target — сколько полных товаров нужно (необязательно, 10)

Выход — JSON-массив из трёх полей: article, name, price.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

__all__ = [
    "DEFAULT_SAMPLE",
    "DEFAULT_TARGET",
    "MAX_LIMIT",
    "OUTPUT_FIELDS",
    "parse_query",
    "parse_all",
    "load_queries",
    "write_results",
]

DEFAULT_SAMPLE = 20  # сколько карточек берём со страницы поиска
DEFAULT_TARGET = 10  # сколько полных товаров нужно в ответе
MAX_LIMIT = 60  # больше карточек с одной страницы WB не отдаёт
OUTPUT_FIELDS = ("article", "name", "price")  # контракт выходного элемента

_NUM_RE = re.compile(r"[^0-9,.\-]")


def _to_float(value: Any) -> float | None:
    """Число из числа или строки: 120, '120.50', '1 200,50 ₽'. None — не число."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if not isinstance(value, str):
        return None

    cleaned = _NUM_RE.sub("", value).replace(" ", "").replace("\u00a0", "")
    if not cleaned or cleaned in {",", ".", "-", "+"}:
        return None

    if "," in cleaned and "." in cleaned:  # 1.234,50 или 1,234.50
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")

    try:
        number = float(cleaned)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _positive_int(value: Any, default: int, where: str, field: str) -> int:
    """Цлое поле: None берёт значение по умолчанию."""
    if value is None or value == "":
        return default
    number = _to_float(value)
    if number is None:
        raise ValueError(f"{where}: поле '{field}' должно быть числом, получено {value!r}")
    number = int(number)
    if number < 1:
        raise ValueError(f"{where}: поле '{field}' должно быть >= 1, получено {value!r}")
    return number


def parse_query(raw: Any, index: int | None = None) -> dict[str, Any]:
    """Один элемент входа -> словарь запроса. Ошибка — ValueError с причиной."""
    where = f"запрос #{index}" if index is not None else "запрос"
    if not isinstance(raw, dict):
        raise ValueError(f"{where}: ожидался объект, получено {type(raw).__name__}")

    name = " ".join(str(raw.get("name") or "").split())
    if not name:
        raise ValueError(f"{where}: поле 'name' обязательно и должно быть непустой строкой")

    cost = _to_float(raw.get("cost"))
    if cost is None:
        raise ValueError(
            f"{where}: поле 'cost' обязательно и должно быть числом, получено {raw.get('cost')!r}"
        )
    if cost < 0:
        raise ValueError(f"{where}: поле 'cost' не может быть отрицательным ({cost})")

    target = min(_positive_int(raw.get("target"), DEFAULT_TARGET, where, "target"), MAX_LIMIT)
    sample = min(_positive_int(raw.get("sample"), DEFAULT_SAMPLE, where, "sample"), MAX_LIMIT)

    return {
        "name": name,
        "cost": cost,
        "target": target,
        # карточек должно быть не меньше, чем нужно товаров, иначе цель недостижима
        "sample": max(sample, target),
    }


def _as_items(payload: Any) -> list:
    """Принимает массив запросов или одиночный объект."""
    if isinstance(payload, str):
        return _as_items(json.loads(payload))
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return payload
    raise ValueError(f"Ожидался JSON-массив запросов, получено {type(payload).__name__}")


def parse_all(payload: Any, *, strict: bool = False) -> tuple[list[dict], list[str]]:
    """Весь вход -> (запросы, проблемы).

    По умолчанию битые элементы пропускаются, чтобы один неверный запрос не ронял
    пачку; strict=True прерывается на первой ошибке.
    """
    queries: list[dict] = []
    problems: list[str] = []

    for index, item in enumerate(_as_items(payload)):
        try:
            queries.append(parse_query(item, index))
        except ValueError as exc:
            if strict:
                raise
            problems.append(str(exc))

    if not queries and problems:
        raise ValueError("Ни один запрос не прошёл валидацию:\n  " + "\n  ".join(problems))

    return queries, problems


def load_queries(source: Any, *, strict: bool = False) -> tuple[list[dict], list[str]]:
    """Читает запросы из пути к файлу, JSON-строки или готовой структуры.

    source=None или "-" не поддерживается: вход только из файлов.
    """
    if source is None or source == "-":
        raise ValueError("консольный ввод не поддерживается: укажите путь к файлу")

    if isinstance(source, (str, os.PathLike)) and str(source).lstrip()[:1] not in {"[", "{"}:
        payload = json.loads(Path(source).read_text(encoding="utf-8-sig"))
    elif hasattr(source, "read"):
        payload = json.load(source)
    elif isinstance(source, str):
        payload = json.loads(source)
    else:
        payload = source

    return parse_all(payload, strict=strict)


def write_results(products: list[dict], destination: Any, *, indent: int = 2) -> str | None:
    """Записывает товары в файл. destination='-' — stdout. Возвращает путь.

    Пишем сначала во временный файл рядом, потом переименовываем. Так читающая
    программа никогда не увидит половину JSON.
    """
    items = [{field: product.get(field) for field in OUTPUT_FIELDS} for product in products]
    text = json.dumps(items, ensure_ascii=False, indent=indent)

    if destination == "-":
        sys.stdout.write(text + "\n")
        sys.stdout.flush()
        return None

    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=str(path.parent),
            prefix=path.name + ".", suffix=".tmp", delete=False,
        ) as tmp:
            tmp_name = tmp.name
            tmp.write(text)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_name, path)
        tmp_name = None
    finally:
        if tmp_name and os.path.exists(tmp_name):
            os.unlink(tmp_name)

    return str(path)