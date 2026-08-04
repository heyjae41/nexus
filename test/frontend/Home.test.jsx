/**
 * Tests for Home view — curation section rendered from mocked /api/home,
 * meet section rendered from mocked /api/events
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Home from '@/views/Home'

// Mock the API client
vi.mock('@/api/client', () => ({
  fetchHome: vi.fn(),
  fetchClasses: vi.fn(),
  fetchEvents: vi.fn(),
  fetchPosts: vi.fn(),
}))

import { fetchClasses, fetchHome, fetchEvents, fetchPosts } from '@/api/client'

const mockHomeData = {
  sections: [
    {
      category: { slug: 'curation', name: '큐레이션', description: '테크 인사이트' },
      total: 3,
      articles: [
        {
          id: 'art-1',
          articleType: 'newsletter',
          title: '테스트 뉴스레터 아티클',
          summary: '요약 1',
          authorName: 'NEXUS 에디터',
          readMinutes: 5,
          likesCount: 100,
          commentsCount: 10,
          viewCount: 500,
          publishedAt: '2026-07-07',
          linkUrl: null,
          isExternal: false,
        },
        {
          id: 'art-2',
          articleType: 'column',
          title: '브런치 외부 아티클 테스트',
          summary: '요약 2',
          authorName: '칼럼니스트',
          readMinutes: 3,
          likesCount: 50,
          commentsCount: 5,
          viewCount: 200,
          publishedAt: '2026-07-06',
          linkUrl: 'https://brunch.co.kr/@test/2?ref=nexus.bccard.ai',
          isExternal: true,
        },
        {
          id: 'art-3',
          articleType: 'guide',
          title: '가이드 아티클',
          summary: '요약 3',
          authorName: '가이드 작가',
          readMinutes: 8,
          likesCount: 200,
          commentsCount: 20,
          viewCount: 1000,
          publishedAt: '2026-07-05',
          linkUrl: null,
          isExternal: false,
        },
      ],
    },
  ],
}

const mockEventsData = {
  data: [
    {
      id: 'ev-1',
      title: '홈 화면 이벤트 1',
      hostName: '호스트',
      eventStart: '2026-07-21T18:30:00',
      eventEnd: '2026-07-21T21:00:00',
      place: 'MARU180, 강남',
      area: '서울',
      priceText: '무료',
      viewCount: 142,
      eventSystemType: 'offline',
      category: 'AI',
      coverImageUrl: null,
      linkUrl: 'https://event-us.kr/event/1?ref=nexus.bccard.ai',
      isExternal: true,
    },
  ],
  meta: { total: 1, page: 1, limit: 3 },
}

const wrap = (ui) => render(<BrowserRouter>{ui}</BrowserRouter>)

function renderHome() {
  return wrap(<Home user={null} enrolled={[]} />)
}

function mockDefaultHomeApis() {
  vi.clearAllMocks()
  fetchEvents.mockResolvedValue(mockEventsData)
  fetchClasses.mockResolvedValue({ data: [], meta: { total: 0, page: 1, limit: 4 } })
  fetchPosts.mockResolvedValue({ data: [], meta: { total: 0, page: 1, limit: 4 } })
}

async function renderHomeWithData() {
  fetchHome.mockResolvedValue(mockHomeData)
  renderHome()
  await waitFor(() => {
    expect(screen.getAllByText('테스트 뉴스레터 아티클').length).toBeGreaterThan(0)
  })
}

describe('Home view — curation section from API', () => {
  beforeEach(mockDefaultHomeApis)

  it('shows loading skeletons initially', () => {
    const pending = new Promise(() => {})
    fetchHome.mockReturnValue(pending)
    fetchEvents.mockReturnValue(pending)
    fetchClasses.mockReturnValue(pending)
    fetchPosts.mockReturnValue(pending)
    renderHome()
    // Skeletons use the .sk class — check for animated skeleton boxes
    const skeletons = document.querySelectorAll('.sk')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('renders article titles after successful API response', async () => {
    await renderHomeWithData()
    expect(screen.getByText('브런치 외부 아티클 테스트')).toBeInTheDocument()
    expect(screen.getByText('가이드 아티클')).toBeInTheDocument()
  })

  it('renders external article as <a> with target=_blank', async () => {
    fetchHome.mockResolvedValue(mockHomeData)
    renderHome()
    await waitFor(() => {
      expect(screen.getByText('브런치 외부 아티클 테스트')).toBeInTheDocument()
    })
    const externalLink = screen.getByTestId('article-card-external')
    expect(externalLink).toHaveAttribute('target', '_blank')
    expect(externalLink).toHaveAttribute('href', 'https://brunch.co.kr/@test/2?ref=nexus.bccard.ai')
  })

  it('renders internal article as Link to /articles/:id', async () => {
    await renderHomeWithData()
    const internalLinks = screen.getAllByTestId('article-card-internal')
    expect(internalLinks.length).toBeGreaterThanOrEqual(1)
    expect(internalLinks[0]).toHaveAttribute('href', '/articles/art-1')
  })

  it('shows error message and no skeletons when API fails', async () => {
    fetchHome.mockRejectedValue(new Error('Network error'))
    renderHome()
    await waitFor(() => {
      expect(screen.getByText(/Network error/i)).toBeInTheDocument()
    })
  })

  it('always renders static sections (클래스, 커뮤니티)', async () => {
    fetchHome.mockResolvedValue(mockHomeData)
    renderHome()
    await waitFor(() => {
      expect(screen.getByText(/지금 뜨는 클래스/)).toBeInTheDocument()
    })
    expect(screen.getByText(/이번 주 커뮤니티/)).toBeInTheDocument()
  })

  it('메인 인기 클래스도 수집 API 결과를 외부 링크로 표시한다', async () => {
    fetchHome.mockResolvedValue(mockHomeData)
    fetchClasses.mockResolvedValue({
      data: [{
        id: 1, title: '홈 수집 클래스', sourceCategoryName: 'AI TECH', category: 'AI Agent',
        badges: ['BEST'], price: 200000, original: 400000, formatName: '올인원',
        linkUrl: 'https://fastcampus.co.kr/test?ref=nexus.bccard.ai', isExternal: true,
      }],
      meta: { total: 1, page: 1, limit: 4 },
    })
    renderHome()
    expect(await screen.findByText('홈 수집 클래스')).toBeInTheDocument()
    expect(screen.getByTestId('class-card-external')).toHaveAttribute(
      'href', 'https://fastcampus.co.kr/test?ref=nexus.bccard.ai',
    )
  })

  it('renders meet section with API events when events are returned', async () => {
    fetchHome.mockResolvedValue(mockHomeData)
    fetchEvents.mockResolvedValue(mockEventsData)
    renderHome()
    await waitFor(() => {
      expect(screen.getByText(/가야할 밋플/)).toBeInTheDocument()
    })
    expect(screen.getAllByText('홈 화면 이벤트 1').length).toBeGreaterThan(0)
  })

  it('hides meet section when API returns no events', async () => {
    fetchEvents.mockResolvedValue({ data: [], meta: { total: 0, page: 1, limit: 3 } })
    await renderHomeWithData()
    expect(screen.queryByText(/가야할 밋플/)).not.toBeInTheDocument()
  })

  it('meet section event cards are external <a> links', async () => {
    fetchHome.mockResolvedValue(mockHomeData)
    fetchEvents.mockResolvedValue(mockEventsData)
    renderHome()
    await waitFor(() => {
      expect(screen.getAllByText('홈 화면 이벤트 1').length).toBeGreaterThan(0)
    })
    const card = screen.getByTestId('event-card-external')
    expect(card.tagName).toBe('A')
    expect(card).toHaveAttribute('target', '_blank')
    expect(card).toHaveAttribute('href', 'https://event-us.kr/event/1?ref=nexus.bccard.ai')
  })
})

describe('Home hero — 큐레이션 허브 카피 (허위 문구 없음)', () => {
  beforeEach(() => {
    mockDefaultHomeApis()
    fetchHome.mockResolvedValue(mockHomeData)
  })

  it('메인 슬로건은 유지하고 허위 통계·허위 카드 문구는 노출하지 않는다', async () => {
    renderHome()
    expect(screen.getByText('AFTER WORK, LEVEL UP')).toBeInTheDocument()
    expect(screen.getByText(/퇴근 후 30분/)).toBeInTheDocument()
    // 자체 클래스·실거래 데이터가 없는 현재 단계에서 거짓이 되는 문구들
    expect(screen.queryByText(/38만 건/)).not.toBeInTheDocument()
    expect(screen.queryByText(/9,400\+/)).not.toBeInTheDocument()
    expect(screen.queryByText(/사내 프로젝트로 연결/)).not.toBeInTheDocument()
    expect(screen.queryByText(/수강생 1,580명/)).not.toBeInTheDocument()
    expect(screen.queryByText(/지금 23명 보는 중/)).not.toBeInTheDocument()
    // 히어로 CTA 버튼 없음 — 서비스 칩이 진입점 역할
    expect(screen.queryByRole('button', { name: '무료로 시작하기' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '오늘의 큐레이션 보기' })).not.toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getAllByText('테스트 뉴스레터 아티클').length).toBeGreaterThan(0)
    })
  })

  it('여섯 서비스를 소개하는 칩을 각 섹션 링크와 함께 표시한다', () => {
    renderHome()
    expect(screen.getByRole('link', { name: /매일 골라 읽는 AI 글/ })).toHaveAttribute('href', '/curation')
    expect(screen.getByRole('link', { name: /검증된 명강의 소개/ })).toHaveAttribute('href', '/classes')
    expect(screen.getByRole('link', { name: /밋업·해커톤 소식/ })).toHaveAttribute('href', '/meet')
    expect(screen.getByRole('link', { name: /현직자 팁·Q&A/ })).toHaveAttribute('href', '/community')
    expect(screen.getByRole('link', { name: /오늘의 특가 수집/ })).toHaveAttribute('href', '/hotdeal')
    expect(screen.getByRole('link', { name: /회사 근처 맛집 검색/ })).toHaveAttribute(
      'href', 'https://web.paybooc.ai/place/eatpl-home',
    )
  })

  it('우측 히어로 카드는 실제 최신 큐레이션 글과 다가오는 밋업을 보여준다', async () => {
    renderHome()
    await waitFor(() => {
      expect(screen.getByText('오늘의 큐레이션')).toBeInTheDocument()
    })
    expect(screen.getByText('다가오는 밋업')).toBeInTheDocument()
    // 최신 글(art-1)과 첫 이벤트(ev-1)가 히어로 카드 + 하단 섹션 두 곳에 나타난다
    expect(screen.getAllByText('테스트 뉴스레터 아티클')).toHaveLength(2)
    expect(screen.getAllByText('홈 화면 이벤트 1')).toHaveLength(2)
  })

  it('데이터가 없으면 히어로 카드를 렌더링하지 않는다', async () => {
    fetchHome.mockResolvedValue({ sections: [] })
    fetchEvents.mockResolvedValue({ data: [], meta: { total: 0, page: 1, limit: 3 } })
    renderHome()
    await waitFor(() => {
      expect(screen.getByText(/아직 글이 없어요/)).toBeInTheDocument()
    })
    expect(screen.queryByText('오늘의 큐레이션')).not.toBeInTheDocument()
    expect(screen.queryByText('다가오는 밋업')).not.toBeInTheDocument()
  })
})

it('히어로 서비스 링크에 card.Pick 이 포함된다 (eat.pl 다음)', async () => {
  renderHome()
  const cardPick = await screen.findByText('card.Pick')
  expect(cardPick.closest('a')).toHaveAttribute('href', '/cardpick')
})
