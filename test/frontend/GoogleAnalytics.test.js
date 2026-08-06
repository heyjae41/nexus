import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const GA_ID = 'G-YCKV0L1G97'
// vitest 는 frontend/ 를 루트로 실행된다 (게이트: cd frontend && npx vitest run)
const indexHtml = readFileSync(resolve(process.cwd(), 'index.html'), 'utf-8')

describe('구글 애널리틱스 태그 (index.html)', () => {
  it('gtag.js 로더가 측정 ID와 함께 async 로 삽입되어 있다', () => {
    expect(indexHtml).toContain(
      `<script async src="https://www.googletagmanager.com/gtag/js?id=${GA_ID}"></script>`,
    )
  })

  it('dataLayer 초기화와 gtag config 가 측정 ID로 설정되어 있다', () => {
    expect(indexHtml).toContain('window.dataLayer = window.dataLayer || []')
    expect(indexHtml).toContain(`gtag('config', '${GA_ID}')`)
  })

  it('태그는 head 안, 앱 번들 로드 전에 위치한다', () => {
    const gaAt = indexHtml.indexOf('googletagmanager.com/gtag/js')
    const headEndAt = indexHtml.indexOf('</head>')
    const appAt = indexHtml.indexOf('/src/main.jsx')
    expect(gaAt).toBeGreaterThan(-1)
    expect(gaAt).toBeLessThan(headEndAt)
    expect(gaAt).toBeLessThan(appAt)
  })
})
