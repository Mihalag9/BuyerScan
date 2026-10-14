import type { MarketResult, MarketStats } from '../lib/api';
import { money, num, wbProductUrl } from '../lib/format';
import { IconExternal } from './icons';

interface MarketPanelProps {
  market: MarketResult | null;
  searchQuery: string;
  loading?: boolean;
}

/** Мини-визуализация диапазона цен. */
function PriceScale({ stats }: { stats: MarketStats }) {
  const { min, max, avg, median } = stats;
  if (!min || !max || min === max) return null;

  const range = max - min;
  const pos = (v: number) => Math.round(((v - min) / range) * 100);

  const marks = [
    { label: 'мин', v: min, cls: 'below' },
    { label: 'медиана', v: median, cls: 'above' },
    { label: 'средняя', v: avg, cls: 'below' },
    { label: 'макс', v: max, cls: 'above' },
  ];

  return (
    <div className="price-scale">
      <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        Диапазон цен
      </div>
      <div className="price-scale-track">
        {marks.map(({ label, v, cls }) => (
          <div
            key={label}
            className={`price-scale-mark ${cls}`}
            style={{ left: `${pos(v)}%` }}
          >
            <span>{money(v)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Аналитика Wildberries: стат-плитки, визуализация цен, таблица. */
export function MarketPanel({ market, searchQuery, loading }: MarketPanelProps) {
  if (loading) {
    return (
      <div className="panel">
        <div className="panel-title">
          <span style={{ fontWeight: 750 }}>Аналитика Wildberries</span>
        </div>
        <div className="skeleton-lines">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 16, width: `${50 + i * 12}%` }} />
          ))}
        </div>
      </div>
    );
  }

  if (!market) return null;

  if (market.error) {
    return (
      <div className="panel">
        <div className="panel-title">
          <span style={{ fontWeight: 750 }}>Аналитика Wildberries</span>
        </div>
        {searchQuery && (
          <p className="muted" style={{ fontSize: 13, marginBottom: 'var(--space-3)' }}>
            Запрос: «{searchQuery}»
          </p>
        )}
        <div className="progress-error">{market.error}</div>
      </div>
    );
  }

  const s = market.stats;
  const products = market.products ?? [];

  if (!products.length) {
    return (
      <div className="panel">
        <div className="panel-title">
          <span style={{ fontWeight: 750 }}>Аналитика Wildberries</span>
        </div>
        {searchQuery && (
          <p className="muted" style={{ fontSize: 13 }}>{`Запрос: «${searchQuery}»`}</p>
        )}
        <div className="progress-error">Похожих товаров не найдено</div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-title">
        <span style={{ fontWeight: 750 }}>Аналитика Wildberries</span>
        {searchQuery && (
          <span className="muted" style={{ marginLeft: 'auto', fontSize: 12 }}>
            «{searchQuery}»
          </span>
        )}
      </div>

      <div className="stats-tiles">
        {[
          { label: 'Минимум', value: money(s.min) },
          { label: 'Средняя', value: money(s.avg) },
          { label: 'Медиана', value: money(s.median) },
          { label: 'Максимум', value: money(s.max) },
          { label: 'Найдено', value: num(s.count ?? products.length) },
        ].map(({ label, value }) => (
          <div key={label} className="stat-tile">
            <span>{label}</span>
            <b>{value}</b>
          </div>
        ))}
      </div>

      {s.min && s.max && s.min !== s.max && <PriceScale stats={s} />}

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Артикул</th>
              <th>Название</th>
              <th>Цена</th>
            </tr>
          </thead>
          <tbody>
            {products.slice(0, 40).map((p) => (
              <tr key={p.article}>
                <td>
                  <a href={wbProductUrl(p.article)} target="_blank" rel="noopener noreferrer">
                    {p.article} <IconExternal size={11} />
                  </a>
                </td>
                <td className="cell-name">{p.name || '—'}</td>
                <td className="num">{money(p.price)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
