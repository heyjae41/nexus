// E2E 스모크 테스트 설정 — 사전 조건: backend + vite 실행 중
// 실행: cd frontend && npx playwright test
// 주소가 다르면 E2E_BASE_URL(웹)·E2E_API(백엔드) 환경변수로 지정 (CI 참고: .github/workflows/ci.yml)
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '../test/e2e',
  timeout: 20_000,
  retries: 0,
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:80',
    screenshot: 'only-on-failure',
  },
  outputDir: '../test/e2e/artifacts',
})
