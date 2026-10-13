// @vitest-environment node
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const GA_ID = 'G-YCKV0L1G97'
// 실행 cwd 와 무관하게 테스트 파일 위치 기준으로 해석한다
const read = (rel) => readFileSync(fileURLToPath(new URL(rel, import.meta.url)), 'utf-8')
const indexHtml = read('../../frontend/index.html')
// 부트스트랩은 CSP(script-src 'self') 때문에 인라인이 아니라 정적 파일이다
const gaInit = read('../../frontend/public/ga-init.js')

describe('구글 애널리틱스 태그 (index.html)', () => {
  it('gtag.js 로더가 측정 ID와 함께 async 로 삽입되어 있다', () => {
    expect(indexHtml).toContain(
      `<script async src="https://www.googletagmanager.com/gtag/js?id=${GA_ID}"></script>`,
    )
  })

  it('부트스트랩(public/ga-init.js)이 head 에서 로드되고 dataLayer·gtag config 를 설정한다', () => {
    expect(indexHtml).toContain('<script src="/ga-init.js"></script>')
    expect(gaInit).toContain('window.dataLayer = window.dataLayer || []')
    expect(gaInit).toContain(`gtag('config', '${GA_ID}'`)
  })

  it('자동 page_view 는 끈다 — 라우터 훅이 제목 설정 후 수동 전송한다', () => {
    expect(gaInit).toContain(`gtag('config', '${GA_ID}', { send_page_view: false })`)
  })

  it('태그는 head 안, 앱 번들 로드 전에 위치한다', () => {
    const gaAt = indexHtml.indexOf('googletagmanager.com/gtag/js')
    const headEndAt = indexHtml.indexOf('</head>')
    const appAt = indexHtml.indexOf('/src/main.jsx')
    expect(gaAt).toBeGreaterThan(-1)
    expect(gaAt).toBeLessThan(headEndAt)
    expect(gaAt).toBeLessThan(appAt)
  })

  it('로컬(localhost/127.0.0.1) 트래픽은 opt-out 플래그로 수집을 차단한다', () => {
    expect(gaInit).toContain(`window['ga-disable-${GA_ID}'] = true`)
    expect(gaInit).toContain("['localhost', '127.0.0.1'].includes(window.location.hostname)")
  })

  it('googletagmanager.com preconnect 가 선언되어 있다', () => {
    expect(indexHtml).toContain('<link rel="preconnect" href="https://www.googletagmanager.com" />')
  })
})
