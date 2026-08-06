// @vitest-environment node
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

// 배포 반영 지연 사고 회귀 가드 (2026-08-06): Cache-Control 없는 index.html 을
// 브라우저가 휴리스틱 캐시로 재검증 없이 사용해, 배포 후에도 기존 방문자에게
// 구버전 앱(GA 미적용)이 실행됐다.
const nginxConf = readFileSync(
  fileURLToPath(new URL('../../docker/nginx.conf', import.meta.url)),
  'utf-8',
)

const spaBlock = nginxConf.match(/location \/ \{[^}]*\}/)?.[0] ?? ''
const assetsBlock = nginxConf.match(/location \/assets\/ \{[^}]*\}/)?.[0] ?? ''

describe('nginx 캐시 헤더 (docker/nginx.conf)', () => {
  it('index.html(SPA 진입점)은 no-cache 로 항상 재검증한다 — 배포 즉시 반영', () => {
    expect(spaBlock).toContain('add_header Cache-Control "no-cache"')
    expect(spaBlock).not.toContain('immutable')
  })

  it('해시된 /assets/ 번들은 장기 캐시(immutable)한다', () => {
    expect(assetsBlock).toContain('add_header Cache-Control "public, max-age=31536000, immutable"')
    expect(assetsBlock).not.toContain('no-cache')
  })
})
