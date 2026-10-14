import { useState } from 'react';
import type { DetectResult } from '../lib/api';
import { percent } from '../lib/format';
import { IconCopy, IconCheck } from './icons';
import { useToast } from './Toast';

interface VisionCardProps {
  detect: DetectResult | null;
  loading?: boolean;
}

function CopyButton({ text }: { text: string }) {
  const { push } = useToast();
  const [copied, setCopied] = useState(false);

  return (
    <button
      className="copy-btn"
      onClick={() => {
        navigator.clipboard.writeText(text).then(() => {
          setCopied(true);
          push('success', 'Скопировано');
          setTimeout(() => setCopied(false), 1500);
        });
      }}
      aria-label="Скопировать"
    >
      {copied ? <IconCheck size={12} /> : <IconCopy size={12} />}
    </button>
  );
}

/** Карточка результатов GigaChat Vision. */
export function VisionCard({ detect, loading }: VisionCardProps) {
  if (loading) {
    return (
      <div className="panel">
        <div className="panel-title">
          <span style={{ fontWeight: 750 }}>GigaChat Vision</span>
        </div>
        <div className="skeleton-lines">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 18, width: `${60 + i * 8}%` }} />
          ))}
        </div>
      </div>
    );
  }

  if (!detect) return null;

  const conf = detect.confidence ?? 0;
  const confPct = Math.round(conf * 100);
  // Цвет дуги уверенности.
  const confColor = conf >= 0.8 ? 'var(--ok)' : conf >= 0.5 ? 'var(--accent)' : 'var(--warn)';
  const R = 20;
  const CIRC = 2 * Math.PI * R;

  return (
    <div className="panel">
      <div className="panel-title">
        <span style={{ fontWeight: 750 }}>GigaChat Vision</span>
        {detect.confidence != null && (
          <span
            style={{
              marginLeft: 'auto',
              fontSize: 12,
              fontWeight: 700,
              color: confColor,
              background: conf >= 0.8 ? 'var(--ok-soft)' : conf >= 0.5 ? 'var(--accent-soft)' : 'var(--warn-soft)',
              padding: '3px 10px',
              borderRadius: 999,
            }}
          >
            {percent(conf)}
          </span>
        )}
      </div>

      {/* Дуга уверенности */}
      {detect.confidence != null && (
        <div className="confidence" style={{ marginBottom: 'var(--space-4)' }}>
          <div className="confidence-ring">
            <svg width={52} height={52} viewBox="0 0 52 52">
              <circle className="track" cx={26} cy={26} r={R} />
              <circle
                className="fill"
                cx={26}
                cy={26}
                r={R}
                stroke={confColor}
                strokeDasharray={CIRC}
                strokeDashoffset={CIRC * (1 - conf)}
              />
            </svg>
            <b style={{ color: confColor }}>{confPct}</b>
          </div>
          <div>
            <div style={{ fontWeight: 700 }}>{detect.product}</div>
            <div className="muted" style={{ fontSize: 13 }}>{detect.category}</div>
          </div>
        </div>
      )}

      <dl>
        {detect.title && (
          <div className="kv">
            <dt>Заголовок</dt>
            <dd style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {detect.title}
              <CopyButton text={detect.title} />
            </dd>
          </div>
        )}
        {detect.description && (
          <div className="kv">
            <dt>Описание</dt>
            <dd style={{ display: 'flex', alignItems: 'flex-start', gap: 6 }}>
              {detect.description}
              <CopyButton text={detect.description} />
            </dd>
          </div>
        )}
        {detect.search_query && (
          <div className="kv">
            <dt>Запрос WB</dt>
            <dd>{detect.search_query}</dd>
          </div>
        )}
        {detect.benefits?.length > 0 && (
          <div className="kv">
            <dt>Преимущества</dt>
            <dd>
              <div className="chips">
                {detect.benefits.map((b, i) => (
                  <span key={i} className="chip">{b}</span>
                ))}
              </div>
            </dd>
          </div>
        )}
        {detect.keywords?.length > 0 && (
          <div className="kv">
            <dt>Ключевые слова</dt>
            <dd>
              <div className="chips">
                {detect.keywords.map((k, i) => (
                  <span key={i} className="chip chip-neutral">{k}</span>
                ))}
              </div>
            </dd>
          </div>
        )}
      </dl>
    </div>
  );
}
