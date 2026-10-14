import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { registerSW } from 'virtual:pwa-register';
import App from './App';
import { ToastProvider } from './components/Toast';
import './styles/tokens.css';
import './styles/base.css';
import './styles/ui.css';

// Регистрация service worker: при обновлении — тост с кнопкой перезагрузки.
registerSW({
  immediate: true,
  onOfflineReady() {
    // Офлайн-оболочка закеширована — тихо готово.
  },
  onNeedRefresh() {
    const ok = window.confirm('Доступна новая версия BuyerScan. Перезагрузить?');
    if (ok) window.location.reload();
  },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ToastProvider>
      <App />
    </ToastProvider>
  </StrictMode>,
);
