"""Сеть: получение товаров Wildberries без токена.

Алгоритм:

  1. Браузер (SeleniumBase, uc=True) ищет по названию на сайте и собирает
     артикулы с ценами. Прокручиваем страницу и ждём — цены подгружаются
     отдельным запросом и в разметке появляются не сразу.
  2. По артикулам параллельно забираем оставшуюся информацию с Basket CDN
     (название). Номер бакета в URL не указан — опрашиваем 01..36 и берём
     первый ответивший.

Тэги в поиск не подставляются: WB их не понимает, а запрос только портит выдачу.
"""

from __future__ import annotations

import gzip
import json
import random
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

try:  # одинаково работает и как скрипт, и как часть пакета
    from wb_schema import DEFAULT_SAMPLE, DEFAULT_TARGET, MAX_LIMIT
except ImportError:  # pragma: no cover
    from .wb_schema import DEFAULT_SAMPLE, DEFAULT_TARGET, MAX_LIMIT  # type: ignore[no-redef]

__all__ = ["search", "set_progress", "OFFICIAL_URL", "PUBLIC_URL"]

OFFICIAL_URL = "https://common-api.wildberries.ru/api/v2/content/v2/search/catalog"
PUBLIC_URL = "https://card.wb.ru/search/v2/"
BASKET_URL = "https://basket-{n:02d}.wbbasket.ru/vol{vol}/part{part}/{aid}/info/ru/card.json"
SEARCH_PAGE = "https://www.wildberries.ru/catalog/0/search.aspx?search={query}"

CARD_SELECTOR = "article.product-card"

#: Всё нужное снимаем одним куском JS: страница WB перерисовывает карточки на лету,
#: и элементы успевают устареть, пока мы читаем их по одному.
COLLECT_JS = """
const cards = Array.from(document.querySelectorAll('article.product-card')).slice(0, arguments[0]);
const pick = (root, sel) => root.querySelector(sel);
const text = (el) => el ? (el.innerText || el.textContent || '').trim() : '';
return cards.map(card => {
  const article = card.getAttribute('data-nm-id');
  let price = text(pick(card, 'ins'));
  if (!price) price = text(pick(card, '[class*="price__lower"], [class*="lower-price"]'));
  if (!price) price = text(pick(card, '[class*="price-current"], .product-card__price'));
  return { article: article, price: price };
});
"""

#: Порядок опроса бакетов — по фактическим попаданиям в реальных прогонах.
_BASKET_ORDER = (15, 17, 18, 19, 20, 21, 22, 23, 16, 14, 12, 26,
                 30, 34, 36, 13, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1,
                 31, 32, 33, 35, 24, 25, 27, 28, 29)

BASKET_FAST = 12.0  # замерено: CDN отвечает 1-13 с, короче таймаута часть валидных бакетов теряется
BASKET_SLOW = 20.0  # последняя попытка для тех, кто не ответил
BASKET_FAST_COUNT = 36  # в первом проходе идём по всему списку, повтор нужен редко
PRICE_WAIT = 1.0  # пауза после прокрутки, пока подгрузятся цены
POOL_SIZE = 60  # ответы CDN долгие, поэтому запросов много
ARTICLES_AT_ONCE = 4  # сколько карточек тянем с CDN одновременно

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept-Encoding": "gzip",
}

_FATAL = frozenset({400, 401, 403, 404})  # повтор тут не поможет

_browser_lock = threading.Lock()  # Selenium не потокобезопасен

_progress = None  # куда писать отчёты о ходе работы

_basket_cache: dict[int, int] = {}  # том (vol) -> номер бакета: у тома он один
_name_cache: dict[str, str] = {}  # артикул -> название
_pool: ThreadPoolExecutor | None = None


def set_progress(callback) -> None:
    """Подписка на отчёты о ходе работы. По умолчанию клиент молчит.

    Без этого во время ожидания WB не видно, идёт ли запрос вообще.
    """
    global _progress
    _progress = callback


def _report(message: str) -> None:
    if _progress is not None:
        _progress(message)


def _basket_pool() -> ThreadPoolExecutor:
    global _pool
    if _pool is None:
        _pool = ThreadPoolExecutor(max_workers=POOL_SIZE, thread_name_prefix="basket")
    return _pool


# --------------------------------------------------------------------------
# шаг 1: браузер — артикул и цена
# --------------------------------------------------------------------------


def _price_from_text(text: str) -> float | None:
    """'1 234 ₽' -> 1234.0. Берём часть до рубля — это цена со скидкой.

    Копейки учитываем: простое удаление всех не-цифр превратило бы '1 234,50 ₽' в 123450.
    """
    head = text.split("₽")[0] if "₽" in text else text
    cleaned = re.sub(r"[^\d,\s]", "", head).replace(" ", "").replace(" ", "")
    if not cleaned or cleaned in {",", "."}:
        return None
    if "," in cleaned:  # запятая — десятичный разделитель
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _search_browser(query: str, sample: int, attempts: int = 2, timeout: float = 12.0) -> tuple[list[dict] | None, str]:
    """Поиск по названию, снимает sample карточек -> [{'article', 'price'}]."""
    try:
        from seleniumbase import Driver
    except ImportError:
        return None, "не установлен seleniumbase: py -m pip install seleniumbase"

    url = SEARCH_PAGE.format(query=urllib.parse.quote(query))
    error = "выдача поиска пуста"

    for attempt in range(attempts):
        driver = None
        try:
            with _browser_lock:  # Selenium не потокобезопасен
                _report(f"    WB: поднимаю Chrome, поиск «{query}» ({attempt + 1}/{attempts})")
                driver = Driver(uc=True, headless=True)
                driver.uc_open_with_reconnect(url, reconnect_time=3)
                driver.wait_for_element(CARD_SELECTOR, timeout=timeout)
                driver.execute_script("window.scrollTo(0, 1000);")
                time.sleep(PRICE_WAIT)  # цены подгружаются отдельным запросом

                cards = driver.find_elements(CARD_SELECTOR)
                _report(f"    WB: карточек на странице {len(cards)}, беру первые {min(sample, len(cards))}")

                items = [
                    {"article": str(row["article"]), "price": _price_from_text(row["price"])}
                    for row in driver.execute_script(COLLECT_JS, sample)
                    if row.get("article")
                ]
                _report(f"    WB: собрано {len(items)} артикулов, с ценой {sum(1 for i in items if i['price'])}")
                if items:
                    return items, ""
                error = "на странице нет карточек товаров"
        except Exception as exc:  # noqa: BLE001 — страница могла не догрузиться
            error = str(exc)
            _report(f"    WB: сбой — {exc}")
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:  # noqa: BLE001
                    pass
        if attempt < attempts - 1:
            time.sleep(1.5)

    return None, error


# --------------------------------------------------------------------------
# шаг 2: Basket CDN — название по артикулу
# --------------------------------------------------------------------------


def _fetch(url: str, body: bytes | None, headers: dict[str, str], attempts: int, timeout: float,
           token_required: bool = False) -> tuple[bytes | None, str | None]:
    """HTTP с ретраями -> (тело ответа, текст ошибки)."""
    last = "неизвестная ошибка"

    for attempt in range(attempts):
        request = urllib.request.Request(url, data=body, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return raw, None
        except urllib.error.HTTPError as exc:
            if exc.code in _FATAL:
                detail = exc.read().decode("utf-8", "replace")[:200]
                if token_required and exc.code in (401, 403):
                    return None, f"токен отвергнут: HTTP {exc.code} {detail}"
                if exc.code == 403:
                    return None, f"WB заблокировал запрос (HTTP 403): {detail}"
                return None, f"HTTP {exc.code} {detail}"
            last = f"HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = str(exc)

        if attempt < attempts - 1:
            time.sleep(min(0.5 * 2**attempt, 8.0) * (0.7 + random.random() * 0.6))  # джиттер

    return None, f"сеть недоступна: {last}"


def _probe(aid: int, vol: int, part: int, basket: int, timeout: float) -> bytes | None:
    raw, _ = _fetch(BASKET_URL.format(n=basket, vol=vol, part=part, aid=aid), None, _HEADERS, 1, timeout)
    return raw


def _race_baskets(aid: int, vol: int, part: int, baskets: list[int], timeout: float) -> tuple[int, bytes] | None:
    """Опрашивает бакеты одновременно и берёт первый ответивший.

    Ответ CDN идёт по 1-10 секунд, поэтому последовательный перебор растягивал бы
    один артикул на полминуты. Неудачные попытки отменяем.
    """
    pool = _basket_pool()
    futures = {pool.submit(_probe, aid, vol, part, b, timeout): b for b in baskets}
    try:
        for future in as_completed(futures):
            raw = future.result()
            if raw:
                return futures[future], raw
    finally:
        for future in futures:
            future.cancel()
    return None


def _title_of(card: dict) -> str:
    return " ".join(str(card.get("imt_name") or card.get("goods_name") or "").split())


def _card_title(article: str) -> str:
    """Название товара по артикулу. Пустая строка — не нашлось."""
    aid = str(article).strip()
    if not aid.isdigit():
        return ""

    aid = int(aid)
    vol, part = aid // 100000, aid // 1000
    known = _basket_cache.get(vol)

    if known:  # том уже знаком — один запрос вместо тридцати шести
        _report(f"    CDN: том vol{vol} помним на бакете {known}")
        raw = _probe(aid, vol, part, known, BASKET_SLOW)
        if raw:
            try:
                data = json.loads(raw)
                if isinstance(data, dict) and _title_of(data):
                    return _title_of(data)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

    baskets = ([known] + [b for b in _BASKET_ORDER if b != known]) if known else list(_BASKET_ORDER)

    for index, timeout in enumerate((BASKET_FAST, BASKET_SLOW)):
        # Второй проход — по всему списку, он нужен только тем, кто не попал в верхушку.
        candidates = baskets[:BASKET_FAST_COUNT] if index == 0 else baskets
        hit = _race_baskets(aid, vol, part, candidates, timeout)
        if hit is None:
            continue
        basket, raw = hit
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(data, dict):
            title = _title_of(data)
            if title:
                _basket_cache[vol] = basket  # запоминаем, где нашлось
                _report(f"    CDN: {aid} нашёлся на бакете {basket:02d}")
                return title

    return ""


def _fetch_names(articles: list[str], need: int = 0) -> dict[str, str]:
    """Названия по артикулам -> {article: name}.

    Идём небольшими группами и останавливаемся, как только набралось need:
    каждый лишний артикул — это десятки запросов к CDN впустую.
    """
    wanted = [a for a in dict.fromkeys(articles) if a not in _name_cache]
    found = {a: _name_cache[a] for a in articles if a in _name_cache}
    if not wanted or (need and len(found) >= need):
        return found

    _report(f"    CDN: названия по {len(wanted)} артикулам, нужно {need or len(wanted)}")
    done = 0
    for start in range(0, len(wanted), ARTICLES_AT_ONCE):
        chunk = wanted[start : start + ARTICLES_AT_ONCE]
        with ThreadPoolExecutor(max_workers=len(chunk)) as pool:
            futures = {pool.submit(_card_title, a): a for a in chunk}
            for future in as_completed(futures):
                article, done = futures[future], done + 1
                try:
                    title = future.result()
                except Exception:  # noqa: BLE001 — карточка просто не нашлась
                    title = ""
                if title:
                    _name_cache[article] = title
                    found[article] = title
                    _report(f"    CDN [{done}/{len(wanted)}] {article} — {title[:60]}")
                else:
                    _report(f"    CDN [{done}/{len(wanted)}] {article} — не найден")
        if need and len(found) >= need:
            _report(f"    CDN: хватило {len(found)}, остальные не проверяем")
            break

    return found


# --------------------------------------------------------------------------
# запасные источники: официальный API по токену и витрина
# --------------------------------------------------------------------------


def _price_from_api(item: dict) -> float | None:
    """Цена со скидкой в рублях. product иногда 0 — тогда берём basic."""
    for size in item.get("sizes") or []:
        prices = size.get("price") or {}
        for key in ("product", "v1", "basic"):
            value = prices.get(key)
            if isinstance(value, (int, float)) and value > 0:
                return float(value) / 100.0

    for key in ("salePriceU", "priceU"):
        value = item.get(key)
        if isinstance(value, (int, float)) and value > 0:
            return float(value) / 100.0
    return None


def _pick_items(payload) -> list:
    """Массив товаров: products/productlist, у витрины — в data."""
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []

    sources = [payload]
    if isinstance(payload.get("data"), dict):
        sources.append(payload["data"])

    for source in sources:
        for key in ("products", "productlist"):
            if isinstance(source.get(key), list):
                return source[key]
    return []


def _to_products(items: list) -> list[dict]:
    """Ответ API -> [{'article','name','price'}]."""
    products: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        article = item.get("id") or item.get("nmId")
        name = str(item.get("name") or "").strip()
        price = _price_from_api(item)
        if not article or not name or not price:
            continue
        products.append({"article": str(article), "name": name, "price": round(price, 2)})
    return products


def _search_official(text: str, limit: int, token: str, attempts: int, timeout: float) -> tuple[list[dict] | None, str]:
    """Официальный API -> (товары, ошибка)."""
    body = json.dumps(
        {"filter": {"query": text}, "sort": "popular", "cursor": {"offset": 0, "limit": limit}},
        ensure_ascii=False,
    ).encode("utf-8")

    headers = {**_HEADERS, "Content-Type": "application/json", "Authorization": token}
    raw, error = _fetch(OFFICIAL_URL, body, headers, attempts, timeout, token_required=True)
    if raw is None:
        return None, error or "официальный API недоступен"

    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, f"официальный API вернул не-JSON: {exc}"

    return _to_products(_pick_items(payload))[:limit], ""


def _search_public(text: str, limit: int, attempts: int, timeout: float) -> tuple[list[dict] | None, str]:
    """Витрина без токена -> (товары, ошибка)."""
    params = {
        "appType": "1", "curr": "rub", "dest": "-1257786", "spp": "20",
        "query": text, "resultset": "catalog", "sort": "popular", "limit": limit, "page": 1,
    }
    raw, error = _fetch(f"{PUBLIC_URL}?{urllib.parse.urlencode(params)}", None, _HEADERS, attempts, timeout)
    if raw is None:
        return None, error or "витрина недоступна"

    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, f"витрина вернула не-JSON: {exc}"

    return _to_products(_pick_items(payload))[:limit], ""


# --------------------------------------------------------------------------
# публичная функция
# --------------------------------------------------------------------------


def search(
    text: str,
    sample: int = DEFAULT_SAMPLE,
    target: int = DEFAULT_TARGET,
    token: str | None = None,
    attempts: int = 3,
    timeout: float = 20.0,
    use_browser: bool = True,
) -> list[dict]:
    """Ищет товары по названию -> [{'article','name','price'}].

    sample — сколько карточек взять со страницы поиска.
    target — сколько полных товаров нужно; как только набралось, работа прекращается.

    Порядок источников: официальный API (если токен) -> браузер + CDN -> витрина.
    Бросает RuntimeError, если не сработал ни один источник.
    """
    text = " ".join(str(text).split())  # тэги в поиск не подставляем
    target = max(1, min(int(target or DEFAULT_TARGET), MAX_LIMIT))
    sample = max(target, min(int(sample or DEFAULT_SAMPLE), MAX_LIMIT))
    if not text:
        return []

    failures: list[str] = []

    if token:
        products, error = _search_official(text, sample, token, attempts, timeout)
        if products is not None:
            return products[:target]
        failures.append(f"официальный API: {error}")

    if use_browser:
        found, error = _search_browser(text, sample)
        if found:
            names = _fetch_names([item["article"] for item in found], target)
            products = [
                {
                    "article": item["article"],
                    "name": names.get(item["article"], ""),
                    "price": item["price"],
                }
                for item in found
                if item["price"] and names.get(item["article"])
            ]
            if products:
                _report(f"    готово: {len(products)} полных товаров")
                return products[:target]
            failures.append("браузер: не удалось получить названия с CDN")
        else:
            failures.append(f"браузер: {error}")

    products, error = _search_public(text, sample, attempts, timeout)
    if products is not None:
        return products[:target]
    failures.append(f"витрина: {error}")

    raise RuntimeError(f"не удалось получить товары по запросу «{text}»: " + "; ".join(failures))