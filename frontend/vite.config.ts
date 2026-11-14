import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import { resolve } from 'node:path'

// One public origin for the demo: the browser only talks to Vite, which proxies /api to the local backend.
// xfwd keeps the judge's real IP in X-Forwarded-For so the backend's per-client limits (admin PIN) do not
// treat every visitor as 127.0.0.1. Tunnel hosts (ngrok) must be allow-listed or Vite answers "Blocked request".
const backend = process.env.BACKEND_URL ?? 'http://127.0.0.1:8000'
const proxy = { '/api': { target: backend, changeOrigin: true, xfwd: true } }
const allowedHosts = ['.ngrok-free.app', '.ngrok-free.dev', '.ngrok.app', '.ngrok.dev', '.ngrok.io']

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: { proxy, allowedHosts, fs: { allow: ['..'] } },
  preview: { port: 4173, strictPort: true, proxy, allowedHosts },
  build: { rollupOptions: { input: { main: resolve(import.meta.dirname, 'index.html'), admin: resolve(import.meta.dirname, 'admin.html') } } },
  test: { environment: 'jsdom', globals: true, setupFiles: ['./src/test/setup.ts'], exclude: ['e2e/**', 'node_modules/**'] },
})
