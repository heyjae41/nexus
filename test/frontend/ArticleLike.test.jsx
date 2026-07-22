/**
 * Tests for ArticleDetail — like button optimistic update
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ArticleDetail from '@/views/ArticleDetail'

vi.mock('@/api/client', () => ({
  fetchArticle: vi.fn(),
  fetchArticles: vi.fn(),
  likeArticle: vi.fn(),
}))

// article.css import — mock it so jsdom doesn't choke
vi.mock('@/styles/article.css', () => ({}))
vi.mock('@/components/KeyVisual', () => ({
  default: () => <div data-testid="key-visual" />,
}))

import { fetchArticle, fetchArticles, likeArticle } from '@/api/client'

const mockArticle = {
  id: 'a1',
  articleType: 'newsletter',
  title: '앤스로픽의 역설',
  summary: '프런티어 벤치마크 1위...',
  authorName: '지적 지니',
  readMinutes: 4,
  likesCount: 326,
  commentsCount: 12,
  viewCount: 12840,
  publishedAt: '2026-07-07',
  linkUrl: null,
  isExternal: false,
  bodyHtml: null,
  keyVisualHtml: null,
  sourceUrl: null,
}

function wrap(articleId = 'a1') {
  return render(
    <MemoryRouter initialEntries={[`/articles/${articleId}`]}>
      <Routes>
        <Route path="/articles/:id" element={<ArticleDetail />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ArticleDetail — like button optimistic update', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchArticle.mockResolvedValue(mockArticle)
    fetchArticles.mockResolvedValue({ data: [], articles: [] })
    likeArticle.mockResolvedValue({ likesCount: 327 })
  })

  it('renders the like button', async () => {
    wrap()
    await waitFor(() => {
      const likeBtn = screen.getByRole('button', { name: /좋아요/i })
      expect(likeBtn).toBeInTheDocument()
    })
  })

  it('shows initial like count from API', async () => {
    wrap()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /좋아요 326/i })).toBeInTheDocument()
    })
  })

  it('increments like count optimistically on first click', async () => {
    wrap()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /좋아요 326/i })).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('button', { name: /좋아요 326/i }))
    // Optimistic: immediately shows +1
    expect(screen.getByRole('button', { name: /좋아요 327/i })).toBeInTheDocument()
  })

  it('server-confirmed count is not double-added (no 328 phantom)', async () => {
    wrap()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /좋아요 326/i })).toBeInTheDocument()
    })
    // Like — optimistic +1 (326→327), 서버 확정값도 327 → 그대로 327 (328 아님)
    fireEvent.click(screen.getByRole('button', { name: /좋아요 326/i }))
    await waitFor(() => {
      expect(likeArticle).toHaveBeenCalledTimes(1)
    })
    expect(screen.getByRole('button', { name: /좋아요 327/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /좋아요 328/i })).not.toBeInTheDocument()
  })

  it('decrements like count on second click (toggle off) without re-calling API', async () => {
    wrap()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /좋아요 326/i })).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('button', { name: /좋아요 326/i }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /좋아요 327/i })).toBeInTheDocument()
    })
    // 취소 — 백엔드에 감소 API 가 없으므로 로컬 표시만 되돌리고 추가 POST 는 보내지 않는다
    fireEvent.click(screen.getByRole('button', { name: /좋아요 327/i }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /좋아요 326/i })).toBeInTheDocument()
    })
    expect(likeArticle).toHaveBeenCalledTimes(1)
  })

  it('re-like after cancel does not send another increment (abuse guard)', async () => {
    wrap()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /좋아요 326/i })).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('button', { name: /좋아요 326/i })) // like → POST
    await waitFor(() => {
      expect(likeArticle).toHaveBeenCalledTimes(1)
    })
    fireEvent.click(screen.getByRole('button', { name: /좋아요 327/i })) // 취소 (POST 없음)
    fireEvent.click(screen.getByRole('button', { name: /좋아요 326/i })) // 재좋아요 (POST 없음)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /좋아요 327/i })).toBeInTheDocument()
    })
    expect(likeArticle).toHaveBeenCalledTimes(1) // 세션당 증가 1회
  })

  it('calls likeArticle API on like click', async () => {
    wrap()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /좋아요 326/i })).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('button', { name: /좋아요 326/i }))
    await waitFor(() => {
      expect(likeArticle).toHaveBeenCalledWith('a1')
    })
  })

  it('reverts like on API failure', async () => {
    likeArticle.mockRejectedValue(new Error('네트워크 오류'))
    wrap()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /좋아요 326/i })).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('button', { name: /좋아요 326/i }))
    // Optimistic increment shown first
    expect(screen.getByRole('button', { name: /좋아요 327/i })).toBeInTheDocument()
    // After rejection, reverts to original
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /좋아요 326/i })).toBeInTheDocument()
    })
  })

  it('related list excludes the current article even when API ids are numbers', async () => {
    fetchArticle.mockResolvedValue({ ...mockArticle, id: 1 })
    fetchArticles.mockResolvedValue({
      data: [
        { id: 1, title: '현재 글 자신', articleType: 'guide' },
        { id: 2, title: '다른 글', articleType: 'guide' },
      ],
    })
    wrap('1') // useParams 의 id 는 문자열 '1' — 숫자 id 와 타입이 달라도 걸러야 한다
    await waitFor(() => {
      expect(screen.getByText('다른 글')).toBeInTheDocument()
    })
    expect(screen.queryByText('현재 글 자신')).not.toBeInTheDocument()
  })

  it('shows error UI with retry when fetch fails and no static fallback exists', async () => {
    fetchArticle.mockRejectedValue(new Error('500'))
    wrap('999') // EDITORIAL_ARTICLES 에 없는 id → 빈 화면 대신 에러 안내
    await waitFor(() => {
      expect(screen.getByText(/글을 불러오지 못했습니다/)).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /다시 시도/ })).toBeInTheDocument()
  })

  it('renders the article title from static data for a1', async () => {
    wrap('a1')
    await waitFor(() => {
      expect(screen.getByText('앤스로픽의 역설')).toBeInTheDocument()
    })
  })
})
