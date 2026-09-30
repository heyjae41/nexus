// @vitest-environment node
/**
 * 상세 히어로 요약은 다섯 줄을 넘기지 않는다.
 * jsdom 은 외부 CSS 를 적용하지 않으므로 규칙 존재를 파일에서 확인한다.
 */
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const css = readFileSync(
  new URL('../../frontend/src/styles/article.css', import.meta.url),
  'utf8',
)

describe('상세 요약 줄 수', () => {
  it('.herosub 는 다섯 줄에서 자른다', () => {
    expect(css).toMatch(/\.herosub\s*\{[^}]*-webkit-line-clamp:\s*5/)
    expect(css).toMatch(/\.herosub\s*\{[^}]*overflow:\s*hidden/)
  })
})
