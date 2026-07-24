// @vitest-environment node
/**
 * 본문(dangerouslySetInnerHTML) 안의 이미지가 문단 폭(.art-body max-width)을
 * 넘지 않도록 하는 CSS 규칙을 검증한다 — jsdom 은 외부 CSS 를 적용하지 않으므로
 * 규칙 존재를 파일 수준에서 못박는다 (인제스트 원고의 원본 크기 이미지 오버플로 방지).
 */
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const css = readFileSync(
  new URL('../../frontend/src/styles/article.css', import.meta.url),
  'utf8',
)

describe('본문 이미지 폭 제한', () => {
  it('.art-body img 에 max-width:100% 가 걸려 있다', () => {
    expect(css).toMatch(/\.art-body img\s*\{[^}]*max-width:\s*100%/)
  })

  it('세로 비율 유지를 위해 height:auto 가 함께 걸려 있다', () => {
    expect(css).toMatch(/\.art-body img\s*\{[^}]*height:\s*auto/)
  })
})
