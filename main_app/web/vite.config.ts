import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

const BACKEND = process.env.BACKEND_URL ?? 'http://127.0.0.1:5000'

// Новый PWA-фронт собирается в подпапку /app/, чтобы не перекрывать
// классический интерфейс на '/' (main_app/static/index.html).
const BASE = '/app/'

// Пути API основного сервиса — в dev-режиме проксируются на FastAPI.
const API_PATHS = ['/analyze', '/detect', '/render', '/health', '/uploads', '/generated']

export default defineConfig({
  base: BASE,
  plugins: [
    react(),
    VitePWA({
      registerType: 'prompt',
      includeAssets: ['favicon.svg', 'apple-touch-icon.png'],
      manifest: {
        name: 'BuyerScan — анализ товара и карточки',
        short_name: 'BuyerScan',
        description: 'Фото → GigaChat Vision → аналитика Wildberries → карточки товара',
        id: BASE,
        start_url: BASE,
        scope: BASE,
        display: 'standalone',
        orientation: 'any',
        lang: 'ru',
        dir: 'ltr',
        background_color: '#0d1114',
        theme_color: '#0d7c86',
        categories: ['business', 'productivity'],
        icons: [
          { src: `${BASE}icons/icon-192.png`, sizes: '192x192', type: 'image/png' },
          { src: `${BASE}icons/icon-512.png`, sizes: '512x512', type: 'image/png' },
          { src: `${BASE}icons/maskable-192.png`, sizes: '192x192', type: 'image/png', purpose: 'maskable' },
          { src: `${BASE}icons/maskable-512.png`, sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,webp,ico}'],
        navigateFallback: `${BASE}index.html`,
        navigateFallbackDenylist: [/^\/(?:analyze|detect|render|health|uploads|generated)\b/],
        cleanupOutdatedCaches: true,
        maximumFileSizeToCacheInBytes: 4 * 1024 * 1024,
      },
    }),
  ],
  server: {
    host: true,
    port: 5173,
    proxy: Object.fromEntries(
      API_PATHS.map((p) => [p, { target: BACKEND, changeOrigin: true }]),
    ),
  },
  build: {
    // Классический index.html в ../static остаётся нетронутым.
    outDir: '../static/app',
    emptyOutDir: true,
    sourcemap: false,
  },
})
