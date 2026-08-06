import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { BASE_TITLE, titleForPath, usePageTitle } from '../../frontend/src/utils/pageTitle'

describe('titleForPath — 라우트별 문서 제목', () => {
  it('홈은 기본 제목을 그대로 쓴다', () => {
    expect(titleForPath('/')).toBe(BASE_TITLE)
  })

  it.each([
    ['/curation', '큐레이션 — NEXUS'],
    ['/articles/12', '큐레이션 — NEXUS'],
    ['/classes', '클래스 — NEXUS'],
    ['/classes/3', '클래스 — NEXUS'],
    ['/community', '커뮤니티 — NEXUS'],
    ['/community/write', '커뮤니티 — NEXUS'],
    ['/community/7', '커뮤니티 — NEXUS'],
    ['/meet', 'meet.pl — NEXUS'],
    ['/meet/5', 'meet.pl — NEXUS'],
    ['/hotdeal', 'AI핫딜 — NEXUS'],
    ['/cardpick', 'card.Pick — NEXUS'],
    ['/onboarding', '회원가입 — NEXUS'],
    ['/checkout/2', '수강신청 — NEXUS'],
    ['/dashboard', '대시보드 — NEXUS'],
    ['/profile', '내 정보 — NEXUS'],
  ])('%s → %s (메뉴 명칭과 동일한 섹션명)', (path, expected) => {
    expect(titleForPath(path)).toBe(expected)
  })

  it('알 수 없는 경로는 기본 제목으로 되돌린다', () => {
    expect(titleForPath('/no-such-route')).toBe(BASE_TITLE)
  })
})

describe('usePageTitle — document.title 동기화', () => {
  it('경로 변경에 따라 document.title 을 갱신한다', () => {
    const { rerender } = renderHook(({ path }) => usePageTitle(path), {
      initialProps: { path: '/curation' },
    })
    expect(document.title).toBe('큐레이션 — NEXUS')

    rerender({ path: '/cardpick' })
    expect(document.title).toBe('card.Pick — NEXUS')

    rerender({ path: '/' })
    expect(document.title).toBe(BASE_TITLE)
  })
})
