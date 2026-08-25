import { renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { NAV_LINKS } from '../../frontend/src/components/Nav'
import { BASE_TITLE, titleForPath, usePageTitle } from '../../frontend/src/utils/pageTitle'

afterEach(() => {
  document.title = ''
  delete window.gtag
})

describe('titleForPath — 라우트별 문서 제목', () => {
  it('홈은 기본 제목을 그대로 쓴다', () => {
    expect(titleForPath('/')).toBe(BASE_TITLE)
  })

  it.each([
    ['/curation', '큐레이션 — EDU.AI'],
    ['/articles/12', '큐레이션 — EDU.AI'],
    ['/classes', '클래스 — EDU.AI'],
    ['/classes/3', '클래스 — EDU.AI'],
    ['/community', '커뮤니티 — EDU.AI'],
    ['/community/write', '커뮤니티 — EDU.AI'],
    ['/community/7', '커뮤니티 — EDU.AI'],
    ['/meet', 'meet.pl — EDU.AI'],
    ['/meet/5', 'meet.pl — EDU.AI'],
    ['/hotdeal', 'AI핫딜 — EDU.AI'],
    ['/cardpick', 'card.Pick — EDU.AI'],
    ['/onboarding', '회원가입 — EDU.AI'],
    ['/checkout/2', '수강신청 — EDU.AI'],
    ['/dashboard', '대시보드 — EDU.AI'],
    ['/profile', '내 정보 — EDU.AI'],
  ])('%s → %s (메뉴 명칭과 동일한 섹션명)', (path, expected) => {
    expect(titleForPath(path)).toBe(expected)
  })

  it('알 수 없는 경로는 기본 제목으로 되돌린다', () => {
    expect(titleForPath('/no-such-route')).toBe(BASE_TITLE)
  })

  it('상단 메뉴 표기와 섹션명이 항상 일치한다 (드리프트 가드)', () => {
    for (const { label, path } of NAV_LINKS) {
      const expected = path === '/' ? BASE_TITLE : `${label} — EDU.AI`
      expect(titleForPath(path)).toBe(expected)
    }
  })
})

describe('usePageTitle — document.title 동기화', () => {
  it('경로 변경에 따라 document.title 을 갱신한다', () => {
    const { rerender } = renderHook(({ path }) => usePageTitle(path), {
      initialProps: { path: '/curation' },
    })
    expect(document.title).toBe('큐레이션 — EDU.AI')

    rerender({ path: '/cardpick' })
    expect(document.title).toBe('card.Pick — EDU.AI')

    rerender({ path: '/' })
    expect(document.title).toBe(BASE_TITLE)
  })

  it('제목 설정 후 GA page_view 를 수동 전송한다 (제목 지연 방지)', () => {
    window.gtag = vi.fn()
    const { rerender } = renderHook(({ path }) => usePageTitle(path), {
      initialProps: { path: '/curation' },
    })
    expect(window.gtag).toHaveBeenCalledWith('event', 'page_view', {
      page_title: '큐레이션 — EDU.AI',
      page_location: window.location.href,
    })

    rerender({ path: '/cardpick' })
    expect(window.gtag).toHaveBeenLastCalledWith('event', 'page_view', {
      page_title: 'card.Pick — EDU.AI',
      page_location: window.location.href,
    })
    expect(window.gtag).toHaveBeenCalledTimes(2)
  })

  it('gtag 가 없어도(로컬·테스트 환경) 제목 갱신은 동작한다', () => {
    renderHook(({ path }) => usePageTitle(path), { initialProps: { path: '/meet' } })
    expect(document.title).toBe('meet.pl — EDU.AI')
  })
})
