import { useEffect } from 'react';
import type { CardVariant } from '../lib/api';
import { IconClose, IconExternal } from './icons';

interface LightboxProps {
  variants: CardVariant[];
  index: number;
  onClose: () => void;
  onNavigate: (index: number) => void;
}

/** Лайтбокс: полноэкранный просмотр карточки с навигацией стрелками. */
export function Lightbox({ variants, index, onClose, onNavigate }: LightboxProps) {
  const current = variants[index];
  const hasPrev = index > 0;
  const hasNext = index < variants.length - 1;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowLeft' && index > 0) onNavigate(index - 1);
      if (e.key === 'ArrowRight' && index < variants.length - 1) onNavigate(index + 1);
    };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [index, variants.length, onClose, onNavigate]);

  if (!current) return null;

  return (
    <div
      className="lightbox"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Просмотр карточки"
    >
      <button className="btn btn-icon lightbox-close" onClick={onClose} aria-label="Закрыть">
        <IconClose size={18} />
      </button>

      {hasPrev && (
        <button
          className="btn btn-icon lightbox-nav prev"
          onClick={(e) => {
            e.stopPropagation();
            onNavigate(index - 1);
          }}
          aria-label="Предыдущая карточка"
        >
          ‹
        </button>
      )}
      {hasNext && (
        <button
          className="btn btn-icon lightbox-nav next"
          onClick={(e) => {
            e.stopPropagation();
            onNavigate(index + 1);
          }}
          aria-label="Следующая карточка"
        >
          ›
        </button>
      )}

      <div className="lightbox-body" onClick={(e) => e.stopPropagation()}>
        <img src={current.card_url} alt={current.name} />
        <div className="lightbox-caption">
          <b>{current.name}</b>
          <span>
            {current.layout} · {current.palette}
          </span>
          <span>
            {index + 1} / {variants.length}
          </span>
          <a
            href={current.card_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-ghost"
            style={{ minHeight: 32, padding: '0 12px', fontSize: 12.5 }}
          >
            <IconExternal size={13} />
            Открыть оригинал
          </a>
        </div>
      </div>
    </div>
  );
}
