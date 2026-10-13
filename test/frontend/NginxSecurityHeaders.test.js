// @vitest-environment node
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

// 보안 점검(2026-10) MEDIUM 회귀 가드: 프록시 뒤 Secure 쿠키, 실제 클라이언트 IP 기준
// 레이트리밋, like 레이트리밋 우회, CSP·HSTS 등 보안 헤더, 인라인 스크립트 제거.
const read = (rel) => readFileSync(fileURLToPath(new URL(rel, import.meta.url)), 'utf-8')
const nginxConf = read('../../docker/nginx.conf')
const headersSnippet = read('../../docker/security-headers.conf')
const dockerfile = read('../../docker/frontend.Dockerfile')
const indexHtml = read('../../frontend/index.html')
const gaInit = read('../../frontend/public/ga-init.js')
const viteConfig = read('../../frontend/vite.config.js')

// proxy_pass 의 ${BACKEND_UPSTREAM} 때문에 블록 안의 중괄호 쌍을 허용한다
const locationBlocks = [...nginxConf.matchAll(/location [^{]+\{(?:[^{}]|\$\{[^}]*\})*\}/g)].map((m) => m[0])
const proxyBlocks = locationBlocks.filter((b) => b.includes('proxy_pass'))
const serving = locationBlocks.filter((b) => !b.includes('return 403'))

describe('nginx 프록시 신뢰 경계 (docker/nginx.conf)', () => {
  it('TLS 종단(ALB)이 준 X-Forwarded-Proto 를 그대로 전달한다 — $scheme 은 항상 http', () => {
    expect(nginxConf).toMatch(/map \$http_x_forwarded_proto \$forwarded_proto \{/)
    expect(proxyBlocks.length).toBeGreaterThanOrEqual(3)
    for (const block of proxyBlocks) {
      expect(block).toContain('proxy_set_header X-Forwarded-Proto $forwarded_proto;')
      expect(block).not.toContain('X-Forwarded-Proto $scheme')
    }
  })

  it('레이트리밋은 ALB 주소가 아니라 X-Forwarded-For 의 실제 클라이언트 IP 로 센다', () => {
    expect(nginxConf).toContain('real_ip_header X-Forwarded-For;')
    expect(nginxConf).toContain('real_ip_recursive on;')
    // 신뢰 홉은 ALB 가 있는 VPC 대역뿐 — RFC1918 전체를 신뢰하면 사설 주소 클라이언트가 XFF 를 조작한다
    expect(nginxConf).toMatch(/set_real_ip_from 172\.25\.72\.0\/24;/)
    expect(nginxConf).not.toMatch(/set_real_ip_from (10\.0\.0\.0\/8|172\.16\.0\.0\/12|192\.168\.0\.0\/16);/)
  })

  it('닉네임 존재 확인도 로그인·가입과 같은 레이트리밋을 받는다 (열거 방지)', () => {
    expect(nginxConf).toContain('location ~ ^/api/(auth/(login|register|nickname-available)|members)$ {')
  })

  it('좋아요 레이트리밋은 숫자 변형(+1, 1_0, %201)으로 빠져나갈 수 없다', () => {
    expect(nginxConf).toContain('location ~ ^/api/articles/[^/]+/like$ {')
    expect(nginxConf).not.toContain('location ~ ^/api/articles/[0-9]+/like$')
  })
})

describe('보안 응답 헤더 (docker/security-headers.conf)', () => {
  it('이미지가 스니펫을 복사하고 403 블록을 뺀 모든 location 이 include 한다 (add_header 는 상속되지 않음)', () => {
    expect(dockerfile).toContain('COPY docker/security-headers.conf /etc/nginx/snippets/security-headers.conf')
    expect(serving.length).toBeGreaterThanOrEqual(4)
    for (const block of serving) {
      expect(block).toContain('include /etc/nginx/snippets/security-headers.conf;')
    }
  })

  it('CSP 는 인라인·외부 스크립트를 막고 프레이밍을 금지한다', () => {
    const csp = headersSnippet.match(/Content-Security-Policy "([^"]+)"/)?.[1] ?? ''
    expect(csp).toContain("default-src 'self'")
    expect(csp).toContain("frame-ancestors 'none'")
    expect(csp).toContain("object-src 'none'")
    expect(csp).toContain("base-uri 'self'")
    expect(csp).toContain("form-action 'self'")
    const scriptSrc = csp.match(/script-src ([^;]+)/)?.[1] ?? ''
    expect(scriptSrc).toContain("'self'")
    expect(scriptSrc).toContain('https://*.googletagmanager.com')
    expect(scriptSrc).not.toContain("'unsafe-inline'")
    expect(scriptSrc).not.toContain("'unsafe-eval'")
    // 글 본문 외부 이미지·GA 비콘, 핫픽 API, 폰트 CDN
    expect(csp).toMatch(/img-src [^;]*https:/)
    expect(csp).toMatch(/connect-src [^;]*https:\/\/open\.paybooc\.co\.kr/)
    expect(csp).toMatch(/style-src [^;]*https:\/\/cdn\.jsdelivr\.net/)
    expect(csp).toMatch(/font-src [^;]*https:\/\/fonts\.gstatic\.com/)
  })

  it('HSTS 는 https 로 들어온 요청에만, 나머지 헤더는 항상 붙인다', () => {
    expect(nginxConf).toMatch(/map \$forwarded_proto \$hsts_value \{/)
    expect(headersSnippet).toContain('add_header Strict-Transport-Security $hsts_value always;')
    expect(headersSnippet).toContain('add_header X-Content-Type-Options "nosniff" always;')
    expect(headersSnippet).toContain('add_header X-Frame-Options "DENY" always;')
    expect(headersSnippet).toMatch(/add_header Referrer-Policy "strict-origin-when-cross-origin" always;/)
  })
})

describe('SPA 진입점은 CSP 와 양립한다', () => {
  it('index.html 에 인라인 스크립트가 없다 — GA 부트스트랩은 정적 파일', () => {
    expect(indexHtml).not.toMatch(/<script(?![^>]*\bsrc=)[^>]*>/)
    expect(indexHtml).toContain('<script src="/ga-init.js"></script>')
    expect(gaInit).toContain("send_page_view: false")
    expect(gaInit).toContain("window['ga-disable-G-YCKV0L1G97'] = true")
  })

  it('vite 개발 서버는 기본으로 LAN 에 열리지 않는다 (VITE_DEV_HOST 로 opt-in)', () => {
    expect(viteConfig).toContain("host: process.env.VITE_DEV_HOST || 'localhost'")
    expect(viteConfig).not.toContain("host: '0.0.0.0'")
  })
})
