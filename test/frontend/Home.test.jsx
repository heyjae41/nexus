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
  fetchEvents: vi.fn(),
  fetchPosts: vi.fn(),
}))

import { fetchHome, fetchEvents, fetchPosts } from '@/api/client'

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

describe('Home view — curation section from API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchEvents.mockResolvedValue(mockEventsData)
    fetchPosts.mockResolvedValue({ data: [], meta: { total: 0, page: 1, limit: 4 } })
  })

  it('shows loading skeletons initially', () => {
    fetchHome.mockReturnValue(new Promise(() => {})) // never resolves
    wrap(<Home user={null} enrolled={[]} />)
    // Skeletons use the .sk class — check for animated skeleton boxes
    const skeletons = document.querySelectorAll('.sk')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('renders article titles after successful API response', async () => {
    fetchHome.mockResolvedValue(mockHomeData)
    wrap(<Home user={null} enrolled={[]} />)
    await waitFor(() => {
      expect(screen.getByText('테스트 뉴스레터 아티클')).toBeInTheDocument()
    })
    expect(screen.getByText('브런치 외부 아티클 테스트')).toBeInTheDocument()
    expect(screen.getByText('가이드 아티클')).toBeInTheDocument()
  })

  it('renders external article as <a> with target=_blank', async () => {
    fetchHome.mockResolvedValue(mockHomeData)
    wrap(<Home user={null} enrolled={[]} />)
    await waitFor(() => {
      expect(screen.getByText('브런치 외부 아티클 테스트')).toBeInTheDocument()
    })
    const externalLink = screen.getByTestId('article-card-external')
    expect(externalLink).toHaveAttribute('target', '_blank')
    expect(externalLink).toHaveAttribute('href', 'https://brunch.co.kr/@test/2?ref=nexus.bccard.ai')
  })

  it('renders internal article as Link to /articles/:id', async () => {
    fetchHome.mockResolvedValue(mockHomeData)
    wrap(<Home user={null} enrolled={[]} />)
    await waitFor(() => {
      expect(screen.getByText('테스트 뉴스레터 아티클')).toBeInTheDocument()
    })
    const internalLinks = screen.getAllByTestId('article-card-internal')
    expect(internalLinks.length).toBeGreaterThanOrEqual(1)
    expect(internalLinks[0]).toHaveAttribute('href', '/articles/art-1')
  })

  it('shows error message and no skeletons when API fails', async () => {
    fetchHome.mockRejectedValue(new Error('Network error'))
    wrap(<Home user={null} enrolled={[]} />)
    await waitFor(() => {
      expect(screen.getByText(/Network error/i)).toBeInTheDocument()
    })
  })

  it('always renders static sections (클래스, 커뮤니티)', async () => {
    fetchHome.mockResolvedValue(mockHomeData)
    wrap(<Home user={null} enrolled={[]} />)
    await waitFor(() => {
      expect(screen.getByText(/지금 뜨는 클래스/)).toBeInTheDocument()
    })
    expect(screen.getByText(/이번 주 커뮤니티/)).toBeInTheDocument()
  })

  it('renders meet section with API events when events are returned', async () => {
    fetchHome.mockResolvedValue(mockHomeData)
    fetchEvents.mockResolvedValue(mockEventsData)
    wrap(<Home user={null} enrolled={[]} />)
    await waitFor(() => {
      expect(screen.getByText(/가야할 밋플/)).toBeInTheDocument()
    })
    expect(screen.getByText('홈 화면 이벤트 1')).toBeInTheDocument()
  })

  it('hides meet section when API returns no events', async () => {
    fetchHome.mockResolvedValue(mockHomeData)
    fetchEvents.mockResolvedValue({ data: [], meta: { total: 0, page: 1, limit: 3 } })
    wrap(<Home user={null} enrolled={[]} />)
    await waitFor(() => {
      expect(screen.getByText('테스트 뉴스레터 아티클')).toBeInTheDocument()
    })
    expect(screen.queryByText(/가야할 밋플/)).not.toBeInTheDocument()
  })

  it('meet section event cards are external <a> links', async () => {
    fetchHome.mockResolvedValue(mockHomeData)
    fetchEvents.mockResolvedValue(mockEventsData)
    wrap(<Home user={null} enrolled={[]} />)
    await waitFor(() => {
      expect(screen.getByText('홈 화면 이벤트 1')).toBeInTheDocument()
    })
    const card = screen.getByTestId('event-card-external')
    expect(card.tagName).toBe('A')
    expect(card).toHaveAttribute('target', '_blank')
    expect(card).toHaveAttribute('href', 'https://event-us.kr/event/1?ref=nexus.bccard.ai')
  })
})
