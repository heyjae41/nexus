import { useEffect } from 'react'

export const BASE_TITLE = 'NEXUS — 금융 AI 학습 채널'

// 섹션명은 상단 메뉴(Nav) 표기와 동일하게 유지한다 — GA 페이지 제목 차원과
// 브라우저 탭에서 사용자가 보는 이름이 어긋나지 않게.
const SECTION_TITLES = [
  ['/curation', '큐레이션'],
  ['/articles', '큐레이션'],
  ['/classes', '클래스'],
  ['/community', '커뮤니티'],
  ['/meet', 'meet.pl'],
  ['/hotdeal', 'AI핫딜'],
  ['/cardpick', 'card.Pick'],
  ['/onboarding', '회원가입'],
  ['/checkout', '수강신청'],
  ['/dashboard', '대시보드'],
  ['/profile', '내 정보'],
]

export function titleForPath(pathname) {
  const match = SECTION_TITLES.find(
    ([prefix]) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  )
  return match ? `${match[1]} — NEXUS` : BASE_TITLE
}

export function usePageTitle(pathname) {
  useEffect(() => {
    const title = titleForPath(pathname)
    document.title = title
    // 제목 설정이 끝난 뒤 page_view 를 보내야 GA 페이지 제목 차원이 정확하다
    // (index.html 의 gtag config 는 send_page_view: false)
    if (typeof window.gtag === 'function') {
      window.gtag('event', 'page_view', {
        page_title: title,
        page_location: window.location.href,
      })
    }
  }, [pathname])
}
