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
        target: process.env.VITE_API_BASE || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
