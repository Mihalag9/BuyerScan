"""Главный модуль: берёт запросы из папки input/, кладёт товары в .output/.

Как проходит прогон:

  1. Читаем запросы из файла в input/.
  2. Ищем товары по названию: берём sample карточек с сайта, затем к каждому
     артикулу подтягиваем название. Как только набралось target полных товаров,
     остальные не проверяем.
  3. Если target не набрался — берём втрое больше карточек и ищем ещё раз.
  4. Пишем найденное в .output/.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:  # работает и как скрипт, и как часть пакета
    from wb_client import search, set_progress
    from wb_schema import MAX_LIMIT, load_queries, write_results
except ImportError:  # pragma: no cover
    from .wb_client import search, set_progress  # type: ignore[no-redef]
    from .wb_schema import MAX_LIMIT, load_queries, write_results  # type: ignore[no-redef]

__all__ = ["process", "process_file", "INPUT_DIR", "OUTPUT_DIR", "main"]

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / ".output"

MORE_CARDS = 3  # во сколько раз больше карточек берём при недоборе


def _say(message: str) -> None:
    """Весь ход работы пишем в stderr, а не в stdout: stdout оставляем под данные."""
    print(message, file=sys.stderr, flush=True)


set_progress(_say)  # клиент пишет в тот же поток, так видно каждый шаг


def _pick_products(queries: list[dict], results: list[list[dict]], min_profit: float) -> tuple[list[dict], list[dict], list[int]]:
    """Отбирает товары для ответа: убирает повторы и дешёвые, обрезает до target.

    Возвращает (товары, сводка по запросам, сколько товаров прошло по каждому).
    """
    products: list[dict] = []
    per_query: list[dict] = []
    counts: list[int] = []
    seen: set[str] = set()

    for index, query in enumerate(queries):
        kept = 0
        for product in results[index]:
            price = product.get("price")
            if price is None or price - query["cost"] < min_profit:
                continue  # нет цены или наценка слишком маленькая
            article = product["article"]
            if not article or not product.get("name"):
                continue  # нет названия — такой товар не нужен
            if article in seen:
                continue  # такой артикул уже выше по списку
            seen.add(article)
            products.append(product)
            kept += 1
            if kept >= query["target"]:
                break
        counts.append(kept)
        per_query.append({"name": query["name"], "target": query["target"], "found": kept})

    return products, per_query, counts


def _run_queries(
    source,
    token: str | None,
    workers: int,
    min_profit: float,
    attempts: int,
    timeout: float,
    use_browser: bool,
    try_more: bool,
) -> tuple[list[dict], list[str], list[dict]]:
    """Выполняет все запросы из одного файла -> (товары, ошибки, сводка).

    Сюда же входит повторный поиск, если не набралось target. На диск не пишет.
    """
    queries, problems = load_queries(source)
    errors = list(problems)
    token = token or os.getenv("WB_TOKEN")

    for query in queries:  # сразу показываем, что ищем
        _say(
            f"  запрос: {query['name']!r}, себестоимость {query['cost']}, "
            f"цель {query['target']}, берём {query['sample']} карточек"
        )

    def run(indices: list[int], cards: dict[int, int], label: str) -> list[list[dict]]:
        """Ищет по нескольким запросам сразу, печатая ход работы."""
        found: list[list[dict]] = [[] for _ in queries]
        done = 0
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = {
                pool.submit(
                    search, queries[i]["name"], cards[i], queries[i]["target"],
                    token, attempts, timeout, use_browser,
                ): i
                for i in indices
            }
            for future in as_completed(futures):
                index, done = futures[future], done + 1
                name = queries[index]["name"]
                try:
                    found[index] = future.result()
                    _say(f"  {label} [{done}/{len(indices)}] {name!r}: {len(found[index])} шт.")
                except Exception as exc:  # noqa: BLE001 — причина уходит в errors
                    errors.append(f"{name!r}: {exc}")
                    _say(f"  {label} [{done}/{len(indices)}] {name!r}: ошибка")
        return found

    indices = list(range(len(queries)))
    results = run(indices, {i: queries[i]["sample"] for i in indices}, "поиск  ")
    products, per_query, counts = _pick_products(queries, results, min_profit)

    short = [i for i in indices if counts[i] < queries[i]["target"]]
    more: dict[int, int] = {}
    if short and try_more:
        more = {i: min(queries[i]["sample"] * MORE_CARDS, MAX_LIMIT) for i in short}
        _say(f"  повтор: набрано меньше цели, берём {more[short[0]]} карточек")
        extra = run(short, more, "повтор ")
        for i in short:
            known = {p["article"] for p in results[i]}
            results[i].extend(p for p in extra[i] if p["article"] not in known)
        products, per_query, counts = _pick_products(queries, results, min_profit)

        # Ошибки первого поиска по этим запросам заменяем итоговым статусом.
        names = {queries[i]["name"] for i in short}
        errors = [line for line in errors if not any(f"{n!r}:" in line for n in names)]

    for i in short:
        if counts[i] < queries[i]["target"]:
            hint = f" (повтор брал {more[i]} карточек)" if i in more else ""
            errors.append(
                f"{queries[i]['name']!r}: успешных {counts[i]}, "
                f"меньше цели {queries[i]['target']}{hint}"
            )

    return products, errors, per_query


def process_file(
    source,
    output,
    token: str | None = None,
    workers: int = 4,
    min_profit: float = 0.0,
    attempts: int = 3,
    timeout: float = 20.0,
    use_browser: bool = True,
    try_more: bool = True,
) -> dict:
    """Один файл запросов -> один файл результата."""
    products, errors, per_query = _run_queries(
        source, token, workers, min_profit, attempts, timeout, use_browser, try_more
    )
    written = write_results(products, output)
    return {"total": len(products), "errors": errors, "per_query": per_query, "output": written}


def process(
    input_dir=INPUT_DIR,
    output_dir=OUTPUT_DIR,
    input_name: str | None = None,
    output_name: str | None = None,
    token: str | None = None,
    workers: int = 4,
    min_profit: float = 0.0,
    attempts: int = 3,
    timeout: float = 20.0,
    verbose: bool = False,
    use_browser: bool = True,
    try_more: bool = True,
) -> dict:
    """Обрабатывает папку: input/ -> .output/.

    input_name  — имя файла запросов; None = взять все *.json разом.
    output_name — имя файла результата; None = то же имя, что у запроса.
                  Если задано при нескольких входных файлах, всё попадёт в один.
    min_profit  — минимальная наценка в рублях, товары дешевле отбрасываются.
    try_more    — если не набралось target, взять втрое больше карточек и повторить.
    """
    input_dir, output_dir = Path(input_dir), Path(output_dir)

    if input_name:
        sources = [input_dir / input_name]
    else:
        input_dir.mkdir(parents=True, exist_ok=True)
        sources = sorted(input_dir.glob("*.json"))

    if not sources:
        raise FileNotFoundError(f"в папке {input_dir} нет *.json с запросами")

    missing = [str(p) for p in sources if not p.is_file()]
    if missing:
        raise FileNotFoundError("файл(ы) с запросами не найдены: " + ", ".join(missing))

    files: list[dict] = []
    merged: list[dict] = []

    for number, source in enumerate(sources, 1):
        _say(f"[файл {number}/{len(sources)}] {source.name}")
        started = time.perf_counter()
        try:
            products, errors, _ = _run_queries(
                source, token, workers, min_profit, attempts, timeout, use_browser, try_more
            )
        except Exception as exc:  # noqa: BLE001 — один плохой файл не должен ронять остальные
            products, errors = [], [f"{source.name}: {exc}"]

        if output_name:
            merged.extend(products)
            target = None
        else:
            target = write_results(products, output_dir / source.name)

        files.append(
            {
                "source": str(source),
                "output": str(target) if target else None,
                "total": len(products),
                "errors": errors,
            }
        )

        if verbose:
            for line in errors:
                _say(f"  ! {line}")
        _say(
            f"  готово: {len(products)} товаров за {time.perf_counter() - started:.1f} с"
            f" -> {Path(target).name if target else '(позже всё в один файл)'}"
        )

    combined: str | None = None
    if output_name:
        combined = str(write_results(merged, output_dir / output_name))

    return {
        "files": files,
        "output": combined,
        "total": len(merged) if output_name else sum(item["total"] for item in files),
        "errors": [line for item in files for line in item["errors"]],
    }


# --------------------------------------------------------------------------
# CLI — только параметры, ввода данных с консоли нет
# --------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="wb_parser",
        description="Ищет товары на Wildberries по запросам из input/, пишет результат в .output/.",
    )
    parser.add_argument("-n", "--input-name", default=None, help="имя файла запросов, без него — все *.json")
    parser.add_argument("-O", "--output-name", default=None, help="имя файла результата")
    parser.add_argument("--input-dir", default=str(INPUT_DIR), help="папка с запросами")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR), help="папка для результатов")
    parser.add_argument("--token", default=None, help="токен WB Seller API (или env WB_TOKEN)")
    parser.add_argument("--workers", type=int, default=4, help="сколько запросов искать одновременно")
    parser.add_argument("--min-profit", type=float, default=0.0, help="минимальная наценка, руб.")
    parser.add_argument("--no-escalate", action="store_true", help="не брать больше карточек при недоборе")
    parser.add_argument("--attempts", type=int, default=3, help="сколько раз пробовать один запрос")
    parser.add_argument("--timeout", type=float, default=20.0, help="сколько ждать ответа, сек")
    parser.add_argument("--no-browser", action="store_true", help="не открывать браузер")
    parser.add_argument("-v", "--verbose", action="store_true", help="показать ошибки подробно")
    args = parser.parse_args(argv)

    try:
        stats = process(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            input_name=args.input_name,
            output_name=args.output_name,
            token=args.token,
            workers=args.workers,
            min_profit=args.min_profit,
            try_more=not args.no_escalate,
            attempts=args.attempts,
            timeout=args.timeout,
            verbose=args.verbose,
            use_browser=not args.no_browser,
        )
    except FileNotFoundError as exc:
        _say(str(exc))
        return 2
    except KeyboardInterrupt:
        _say("Прервано")
        return 130

    _say(f"файлов: {len(stats['files'])}, товаров: {stats['total']}, ошибок: {len(stats['errors'])}")
    if not args.verbose:
        for line in stats["errors"]:
            _say(f"  ! {line}")

    return 0 if stats["total"] or not stats["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())