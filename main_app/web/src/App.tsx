import { useCallback, useRef, useState } from 'react';
import { analyzePhoto, type AnalyzeResponse } from './lib/api';
import { isAbortError } from './lib/format';
import { useOnlineStatus } from './lib/hooks';
import { Header } from './components/Header';
import { InstallButton } from './components/InstallButton';
import { OfflineBanner } from './components/OfflineBanner';
import { Dropzone } from './components/Dropzone';
import { OptionsPanel } from './components/OptionsPanel';
import { ProgressTracker, type Phase } from './components/ProgressTracker';
import { VisionCard } from './components/VisionCard';
import { MarketPanel } from './components/MarketPanel';
import { CardsGallery } from './components/CardsGallery';
import { useToast } from './components/Toast';
import { IconRefresh, IconTag, IconTrash } from './components/icons';

interface Options {
  useBrowser: boolean;
  doCutout: boolean;
  purchasePrice: number;
  variantCount: number;
}

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [options, setOptions] = useState<Options>({
    useBrowser: true,
    doCutout: true,
    purchasePrice: 0,
    variantCount: 8,
  });
  const [phase, setPhase] = useState<Phase>('idle');
  const [uploadPct, setUploadPct] = useState(0);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  const online = useOnlineStatus();
  const { push } = useToast();
  const cancelRef = useRef<(() => void) | null>(null);

  const busy = phase === 'uploading' || phase === 'processing';

  const start = useCallback(async () => {
    if (!file) return;
    if (!online) {
      push('error', 'Нет соединения — проверьте интернет и повторите');
      return;
    }

    setPhase('uploading');
    setUploadPct(0);
    setError(null);
    setResult(null);
    setStartedAt(Date.now());

    const { promise, cancel } = analyzePhoto(
      file,
      {
        useBrowser: options.useBrowser,
        doCutout: options.doCutout,
        purchasePrice: options.purchasePrice,
        variantCount: options.variantCount,
      },
      {
        onUploadProgress: (pct) => {
          setUploadPct(pct);
          if (pct >= 100) setPhase('processing');
        },
      },
    );
    cancelRef.current = cancel;

    try {
      const data = await promise;
      setResult(data);
      setPhase('done');
      push('success', 'Анализ завершён');
    } catch (e) {
      if (isAbortError(e)) {
        setPhase('idle');
        return;
      }
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      setPhase('error');
    } finally {
      cancelRef.current = null;
    }
  }, [file, online, options, push]);

  const cancel = useCallback(() => {
    cancelRef.current?.();
    setPhase('idle');
    setStartedAt(null);
  }, []);

  const reset = useCallback(() => {
    cancel();
    setFile(null);
    setResult(null);
    setError(null);
    setPhase('idle');
    setStartedAt(null);
  }, [cancel]);

  const set = <K extends keyof Options>(key: K, value: Options[K]) =>
    setOptions((o) => ({ ...o, [key]: value }));

  return (
    <>
      <Header installButton={<InstallButton />} />
      {!online && <OfflineBanner />}

      <main className="container">
        <section className="hero">
          <h1>Фото → анализ → карточки</h1>
          <p>
            Загрузи фотографию товара: GigaChat Vision распознает его, найдём цены на
            Wildberries и сгенерируем готовые карточки для маркетплейса.
          </p>
          <div className="hero-steps">
            <span>
              <IconTag size={14} /> 1 · Распознавание
            </span>
            <span>
              <IconTag size={14} /> 2 · Аналитика WB
            </span>
            <span>
              <IconTag size={14} /> 3 · Карточки
            </span>
          </div>
        </section>

        <section className="panel" aria-label="Загрузка и параметры">
          <Dropzone file={file} onFile={setFile} disabled={busy} />

          <OptionsPanel
            useBrowser={options.useBrowser}
            onUseBrowser={(v) => set('useBrowser', v)}
            doCutout={options.doCutout}
            onDoCutout={(v) => set('doCutout', v)}
            purchasePrice={options.purchasePrice}
            onPurchasePrice={(v) => set('purchasePrice', v)}
            variantCount={options.variantCount}
            onVariantCount={(v) => set('variantCount', v)}
          />

          <div className="actions-row">
            <button
              className="btn btn-primary btn-lg"
              disabled={!file || busy || !online}
              onClick={start}
            >
              {busy ? 'Анализируем…' : 'Анализировать'}
            </button>
            {phase === 'done' && (
              <button className="btn btn-ghost" onClick={start} disabled={!file}>
                <IconRefresh size={15} />
                Повторить
              </button>
            )}
            <button className="btn btn-ghost" onClick={reset} disabled={busy || !file}>
              <IconTrash size={15} />
              Сбросить
            </button>
          </div>

          {busy && (
            <ProgressTracker
              phase={phase}
              uploadPct={uploadPct}
              startedAt={startedAt}
              error={error}
              onCancel={cancel}
            />
          )}
        </section>

        {phase === 'error' && (
          <div className="panel">
            <ProgressTracker
              phase="error"
              uploadPct={uploadPct}
              startedAt={startedAt}
              error={error}
              onCancel={reset}
            />
          </div>
        )}

        {result && (
          <div className="results-grid">
            <VisionCard detect={result.detect} />
            <MarketPanel market={result.market} searchQuery={result.search_query} />
          </div>
        )}

        {result && <CardsGallery cards={result.cards} />}
      </main>

      <footer className="container footer">
        <span>BuyerScan — инструмент продавцов маркетплейсов</span>
        <span className="muted">
          GigaChat Vision · Wildberries · генератор карточек
        </span>
      </footer>
    </>
  );
}
