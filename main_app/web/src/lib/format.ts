/* Форматирование чисел, денег и времени. */

const nf = new Intl.NumberFormat('ru-RU');

export function money(v: number | null | undefined): string {
  if (v == null || v === 0) return '—';
  return `${nf.format(Math.round(v))} ₽`;
}

export function num(v: number | null | undefined): string {
  if (v == null) return '—';
  return nf.format(v);
}

export function percent(v: number | null | undefined): string {
  if (v == null) return '—';
  return `${Math.round(v * 100)}%`;
}

export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} КБ`;
  return `${(bytes / 1024 / 1024).toFixed(1)} МБ`;
}

export function secondsFmt(sec: number): string {
  if (sec < 60) return `${sec.toFixed(0)} с`;
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m} мин ${String(s).padStart(2, '0')} с`;
}

/** Ссылка на карточку товара на Wildberries по артикулу. */
export function wbProductUrl(article: string): string {
  return `https://www.wildberries.ru/catalog/${encodeURIComponent(article)}/detail.aspx`;
}

export function isAbortError(e: unknown): boolean {
  return e instanceof DOMException && e.name === 'AbortError';
}
