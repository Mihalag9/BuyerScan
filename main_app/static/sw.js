// ВРЕМЕННЫЙ самоуничтожающийся service worker.
// Браузер скачивает его вместо старого workbox-воркера, активируется,
// чистит все кэши, снимает себя с регистрации и перезагружает открытые вкладки.
// После этого файл можно удалить.
self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
      .then(() => self.registration.unregister())
      .then(() => self.clients.matchAll({ type: 'window' }))
      .then((clients) => clients.forEach((c) => c.navigate(c.url))),
  );
});
