// E2E 스모크 테스트 설정 — 사전 조건: backend(8000) + vite(5173) 실행 중
// 실행: cd frontend && npx playwright test
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '../test/e2e',
  timeout: 20_000,
  retries: 0,
  use: {
    baseURL: 'http://localhost:5173',
    screenshot: 'only-on-failure',
  },
  outputDir: '../test/e2e/artifacts',
})
