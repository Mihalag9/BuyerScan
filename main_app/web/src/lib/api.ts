/* Типы ответов бэкенда и функция анализа с прогрессом. */

export interface DetectResult {
  product: string;
  category: string;
  search_query: string;
  title: string;
  description: string;
  benefits: string[];
  keywords: string[];
  confidence: number;
  image_url?: string;
}

export interface MarketProduct {
  article: string;
  name: string;
  price: number;
  url?: string;
}

export interface MarketStats {
  min: number;
  avg: number;
  max: number;
  median: number;
  count: number;
}

export interface MarketResult {
  products: MarketProduct[];
  stats: MarketStats;
  error?: string | null;
}

export interface CutoutInfo {
  enabled: boolean;
  provider?: string;
  usable?: boolean;
  fallback?: string;
}

export interface CardVariant {
  id: string;
  name: string;
  layout: string;
  palette: string;
  card_url: string;
}

export interface CardsResult {
  variants: CardVariant[];
  cutout?: CutoutInfo;
  template_count?: number;
  error?: string | null;
  image_url?: string;
}

export interface AnalyzeResponse {
  detect: DetectResult;
  market: MarketResult;
  cards: CardsResult;
  search_query: string;
}

export interface HealthResponse {
  ok: boolean;
  model?: string;
  analytics?: { ok: boolean; status?: number; error?: string };
  render_url?: string;
  analytics_url?: string;
}

// ──────────────────────────────────────────────────────────────
// Анализ с реальным прогрессом загрузки (XHR) и AbortController.
// ──────────────────────────────────────────────────────────────

export interface AnalyzeOptions {
  useBrowser: boolean;
  doCutout: boolean;
  purchasePrice: number;
  variantCount: number;
}

export interface ProgressCallbacks {
  onUploadProgress?: (pct: number) => void;
  onStatus?: (status: string) => void;
}

let abortController: AbortController | null = null;

/**
 * Запускает POST /analyze с отслеживанием прогресса загрузки.
 * Возвращает promise результата и метод отмены.
 */
export function analyzePhoto(
  file: File,
  options: AnalyzeOptions,
  progress?: ProgressCallbacks,
): { promise: Promise<AnalyzeResponse>; cancel: () => void } {
  // Отменяем предыдущий запрос, если он ещё выполняется.
  if (abortController) abortController.abort();
  const controller = new AbortController();
  abortController = controller;

  const fd = new FormData();
  fd.append('image', file);
  fd.append('sample', '20');
  fd.append('target', '10');
  fd.append('use_browser', options.useBrowser ? 'true' : 'false');
  fd.append('do_cutout', options.doCutout ? 'true' : 'false');
  fd.append('purchase_price', String(options.purchasePrice || 0));
  fd.append('variant_count', String(options.variantCount || 8));

  const xhr = new XMLHttpRequest();

  const promise = new Promise<AnalyzeResponse>((resolve, reject) => {
    xhr.open('POST', '/analyze');

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && progress?.onUploadProgress) {
        progress.onUploadProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as AnalyzeResponse);
        } catch {
          reject(new Error('Некорректный ответ сервера'));
        }
      } else {
        const text = xhr.responseText;
        reject(new Error(`Ошибка сервера (${xhr.status}): ${text.slice(0, 200)}`));
      }
    };

    xhr.onerror = () => reject(new Error('Сеть недоступна'));
    xhr.ontimeout = () => reject(new Error('Превышено время ожидания'));
    xhr.onabort = () => reject(new DOMException('Запрос отменён', 'AbortError'));

    xhr.timeout = 300_000; // 5 минут — на случай долгих WB-аналитик.
    xhr.send(fd);
  });

  return {
    promise,
    cancel: () => {
      controller.abort();
    },
  };
}

/**
 * Проверка здоровья бэкенда.
 */
export async function checkHealth(): Promise<HealthResponse> {
  try {
    const resp = await fetch('/health');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return (await resp.json()) as HealthResponse;
  } catch {
    return { ok: false };
  }
}

// Сброс контроллера отмены.
export function resetAbort() {
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
}
