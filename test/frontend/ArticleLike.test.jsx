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

  it('decrements like count on second click (toggle off)', async () => {
    wrap()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /좋아요 326/i })).toBeInTheDocument()
    })
    // Like — optimistic +1 (326→327), then API confirms likeCount=327 so display becomes 327+1=328
    fireEvent.click(screen.getByRole('button', { name: /좋아요 326/i }))
    // Wait for in-flight guard to clear: API sets likeCount=327, liked=true → display 328
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /좋아요 328/i })).toBeInTheDocument()
    })
    // Unlike — optimistic -1 (328→327)
    fireEvent.click(screen.getByRole('button', { name: /좋아요 328/i }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /좋아요 327/i })).toBeInTheDocument()
    })
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

  it('renders the article title from static data for a1', async () => {
    wrap('a1')
    await waitFor(() => {
      expect(screen.getByText('앤스로픽의 역설')).toBeInTheDocument()
    })
  })
})
