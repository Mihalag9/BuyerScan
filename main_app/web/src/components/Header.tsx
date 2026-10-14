import { useEffect, useState } from 'react';
import { checkHealth, type HealthResponse } from '../lib/api';
import { IconExternal } from './icons';

const BASE = import.meta.env.BASE_URL;

/** Шапка: логотип, статус сервиса, тема, кнопка установки. */
export function Header({ installButton }: { installButton?: React.ReactNode }) {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () => {
      checkHealth().then((h) => {
        if (alive) setHealth(h);
      });
    };
    load();
    const timer = window.setInterval(load, 60_000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);

  const analyticsOk = health?.analytics?.ok;
  const status = health?.ok ? (analyticsOk ? 'ok' : 'warn') : 'down';
  const statusText =
    health === null
      ? 'Проверяю…'
      : status === 'ok'
        ? `Сервис · ${health.model ?? 'OK'}`
        : status === 'warn'
          ? 'Сервис без WB-аналитики'
          : 'Сервис недоступен';

  return (
    <header className="header">
      <div className="container header-inner">
        <a className="logo" href={BASE}>
          <img src={`${BASE}favicon.svg`} alt="" />
          <span>BuyerScan</span>
        </a>
        <div className="header-actions">
          <a
            className="btn btn-ghost"
            href="/"
            style={{ minHeight: 34, padding: '0 12px', fontSize: 13 }}
            title="Классическая версия"
          >
            <IconExternal size={15} />
            <span className="hide-mobile">Классическая</span>
          </a>
          <span
            className={`health-dot ${status === 'warn' ? '' : status}`}
            title={statusText}
          >
            <span>{status === 'ok' ? 'OK' : status === 'warn' ? 'WB ✕' : '✕'}</span>
          </span>
          {installButton}
        </div>
      </div>
    </header>
  );
}
