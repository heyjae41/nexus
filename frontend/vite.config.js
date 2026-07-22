import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { malformedUriGuard } from './vite.malformed-uri-guard.js'

export default defineConfig({
  plugins: [malformedUriGuard(), react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 80,
    strictPort: true,
    proxy: {
      '/api': {
        // API_PROXY_TARGET: 프록시 전용 (VITE_ 접두사가 아니라 클라이언트 번들에 노출되지 않음)
        target: process.env.API_PROXY_TARGET || process.env.VITE_API_BASE || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
