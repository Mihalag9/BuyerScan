import { useEffect, useState } from 'react';
import { secondsFmt } from '../lib/format';
import { IconCheck, IconStop } from './icons';

export type Phase = 'idle' | 'uploading' | 'processing' | 'done' | 'error';

interface ProgressTrackerProps {
  phase: Phase;
  uploadPct: number;
  startedAt: number | null;
  error: string | null;
  onCancel: () => void;
}

/**
 * Прогресс-трекер: этапы, таймер, ошибка, кнопка отмены.
 * При uploadPct=100 и phase=processing — индикатор «неопределённый» (анимация).
 */
export function ProgressTracker({
  phase,
  uploadPct,
  startedAt,
  error,
  onCancel,
}: ProgressTrackerProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!startedAt) return;
    const tick = () => setElapsed((Date.now() - startedAt) / 1000);
    tick();
    const timer = window.setInterval(tick, 500);
    return () => window.clearInterval(timer);
  }, [startedAt]);

  const isDone = phase === 'done';
  const isUploading = phase === 'uploading';
  const isProcessing = phase === 'processing';
  const isError = phase === 'error';

  // При загрузке — реальный процент; при обработке — индетерминированный.
  const barPct = isUploading ? uploadPct : isProcessing ? 50 : isDone ? 100 : 0;

  return (
    <div className="progress" role="progressbar" aria-valuenow={barPct} aria-valuemin={0} aria-valuemax={100}>
      <div className="progress-head">
        <span style={{ fontWeight: 700 }}>
          {isUploading && 'Загрузка файла…'}
          {isProcessing && 'Обрабатываем…'}
          {isDone && 'Готово'}
          {isError && 'Ошибка'}
        </span>
        {startedAt && (
          <span className="progress-timer">{secondsFmt(elapsed)}</span>
        )}
      </div>
      <div className={`progress-bar ${isProcessing ? 'indeterminate' : ''}`}>
        <div className="progress-bar-fill" style={{ width: `${barPct}%` }} />
      </div>

      <div className="stages">
        <div className={`stage ${isUploading ? 'active' : isProcessing || isDone || isError ? 'done' : ''}`}>
          <span className="stage-dot">
            {(isProcessing || isDone || isError) && <IconCheck size={11} />}
          </span>
          <span>Загрузка файла</span>
          {isUploading && <span style={{ marginLeft: 'auto', fontSize: 12 }}>{uploadPct}%</span>}
        </div>

        <div className={`stage ${isProcessing ? 'active' : isDone ? 'done' : isError ? 'done' : ''}`}>
          <span className="stage-dot">
            {(isDone || isError) && <IconCheck size={11} />}
          </span>
          <span>Распознавание → WB-аналитика → рендер карточек</span>
        </div>
      </div>

      {isError && error && (
        <div className="progress-error">{error}</div>
      )}

      {(isUploading || isProcessing) && (
        <div style={{ marginTop: 'var(--space-3)', display: 'flex', gap: 'var(--space-2)' }}>
          <button className="btn btn-danger" onClick={onCancel}>
            <IconStop size={14} />
            Отменить
          </button>
        </div>
      )}
    </div>
  );
}
