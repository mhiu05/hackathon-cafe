import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import { resolve } from 'node:path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } }, fs: { allow: ['..'] } },
  build: { rollupOptions: { input: { main: resolve(import.meta.dirname, 'index.html'), admin: resolve(import.meta.dirname, 'admin.html') } } },
  test: { environment: 'jsdom', globals: true, setupFiles: ['./src/test/setup.ts'], exclude: ['e2e/**', 'node_modules/**'] },
})
