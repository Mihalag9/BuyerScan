import { useState } from 'react';
import type { CardsResult } from '../lib/api';
import { IconExternal } from './icons';
import { Lightbox } from './Lightbox';

interface CardsGalleryProps {
  cards: CardsResult | null;
  loading?: boolean;
}

/** Галерея карточек с лайтбоксом. */
export function CardsGallery({ cards, loading }: CardsGalleryProps) {
  const [lightboxIdx, setLightboxIdx] = useState<number | null>(null);

  if (loading) {
    return (
      <div className="panel">
        <div className="panel-title">
          <span style={{ fontWeight: 750 }}>Карточки товара</span>
        </div>
        <div className="gallery">
          {[...Array(6)].map((_, i) => (
            <div key={i} style={{ display: 'grid', gap: 8 }}>
              <div className="skeleton" style={{ aspectRatio: '3/4' }} />
              <div className="skeleton" style={{ height: 14, width: 70 }} />
              <div className="skeleton" style={{ height: 10, width: 120 }} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!cards) return null;

  if (cards.error) {
    return (
      <div className="panel">
        <div className="panel-title">
          <span style={{ fontWeight: 750 }}>Карточки товара</span>
        </div>
        <div className="progress-error">{cards.error}</div>
      </div>
    );
  }

  const variants = cards.variants ?? [];
  if (!variants.length) {
    return (
      <div className="panel">
        <div className="panel-title">
          <span style={{ fontWeight: 750 }}>Карточки товара</span>
        </div>
        <div className="progress-error">Варианты не сгенерированы</div>
      </div>
    );
  }

  return (
    <>
      <div className="panel">
        <div className="panel-title">
          <span style={{ fontWeight: 750 }}>Карточки товара</span>
          <span className="muted" style={{ marginLeft: 'auto', fontSize: 12 }}>
            {variants.length} вариант{variants.length === 1 ? '' : variants.length < 5 ? 'а' : ''}
            {cards.template_count ? ` · ${cards.template_count} шаблонов` : ''}
          </span>
        </div>

        {/* Cutout info */}
        {cards.cutout?.enabled && (
          <div style={{ marginBottom: 'var(--space-3)', fontSize: 12.5, color: 'var(--ink-3)' }}>
            {cards.cutout.usable === false
              ? '⚠ Сегментация не удалась — использован оригинал'
              : `Вырезание: ${cards.cutout.provider ?? '—'}`}
          </div>
        )}

        <div className="gallery">
          {variants.map((v, i) => (
            <div
              key={v.id}
              className="card-item"
              onClick={() => setLightboxIdx(i)}
              tabIndex={0}
              role="button"
              aria-label={`Карточка ${v.name}`}
            >
              <div className="card-item-thumb">
                <img src={v.card_url} alt={v.name} loading="lazy" />
              </div>
              <div className="card-item-meta">
                <b>{v.name}</b>
                <small>
                  {v.layout} · {v.palette}
                </small>
                <a
                  href={v.card_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  style={{ fontSize: 12 }}
                >
                  <IconExternal size={12} />
                  Открыть оригинал
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>

      {lightboxIdx !== null && (
        <Lightbox
          variants={variants}
          index={lightboxIdx}
          onClose={() => setLightboxIdx(null)}
          onNavigate={setLightboxIdx}
        />
      )}
    </>
  );
}
