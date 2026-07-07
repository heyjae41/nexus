/**
 * Tests for Curation list view — pagination render
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Curation from '@/views/Curation'

vi.mock('@/api/client', () => ({
  fetchArticles: vi.fn(),
}))

import { fetchArticles } from '@/api/client'

function makeArticle(i) {
  return {
    id: `a${i}`,
    articleType: i % 2 === 0 ? 'newsletter' : 'column',
    title: `아티클 제목 ${i}`,
    summary: `요약 ${i}`,
    authorName: `저자 ${i}`,
    readMinutes: 5,
    likesCount: i * 10,
    commentsCount: i,
    viewCount: i * 100,
    publishedAt: '2026-07-07',
    linkUrl: null,
    isExternal: false,
  }
}

const wrap = (ui) => render(<BrowserRouter>{ui}</BrowserRouter>)

describe('Curation list view', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows loading skeletons initially', () => {
    fetchArticles.mockReturnValue(new Promise(() => {}))
    wrap(<Curation />)
    const skeletons = document.querySelectorAll('.sk')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('renders article list after API response', async () => {
    fetchArticles.mockResolvedValue({
      data: [makeArticle(1), makeArticle(2), makeArticle(3)],
      meta: { total: 3, page: 1, limit: 20 },
    })
    wrap(<Curation />)
    await waitFor(() => {
      expect(screen.getByText('아티클 제목 1')).toBeInTheDocument()
    })
    expect(screen.getByText('아티클 제목 2')).toBeInTheDocument()
    expect(screen.getByText('아티클 제목 3')).toBeInTheDocument()
  })

  it('does NOT show pagination when total <= page size', async () => {
    fetchArticles.mockResolvedValue({
      data: Array.from({ length: 5 }, (_, i) => makeArticle(i + 1)),
      meta: { total: 5, page: 1, limit: 20 },
    })
    wrap(<Curation />)
    await waitFor(() => {
      expect(screen.getByText('아티클 제목 1')).toBeInTheDocument()
    })
    // No page "2" button
    expect(screen.queryByRole('button', { name: '2' })).not.toBeInTheDocument()
  })

  it('shows pagination buttons when total > page size (20)', async () => {
    const articles = Array.from({ length: 20 }, (_, i) => makeArticle(i + 1))
    fetchArticles.mockResolvedValue({
      data: articles,
      meta: { total: 45, page: 1, limit: 20 },
    })
    wrap(<Curation />)
    await waitFor(() => {
      expect(screen.getByText('아티클 제목 1')).toBeInTheDocument()
    })
    // Should show 3 page buttons (ceil(45/20) = 3)
    expect(screen.getByRole('button', { name: '1' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '2' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '3' })).toBeInTheDocument()
  })

  it('calls fetchArticles with page 2 when page button clicked', async () => {
    const articles = Array.from({ length: 20 }, (_, i) => makeArticle(i + 1))
    fetchArticles.mockResolvedValue({
      data: articles,
      meta: { total: 40, page: 1, limit: 20 },
    })
    wrap(<Curation />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: '2' })).toBeInTheDocument()
    })
    fetchArticles.mockResolvedValue({
      data: Array.from({ length: 5 }, (_, i) => makeArticle(i + 21)),
      meta: { total: 40, page: 2, limit: 20 },
    })
    fireEvent.click(screen.getByRole('button', { name: '2' }))
    await waitFor(() => {
      expect(fetchArticles).toHaveBeenCalledWith(
        expect.objectContaining({ page: 2 })
      )
    })
  })

  it('shows empty state when API returns no articles', async () => {
    fetchArticles.mockResolvedValue({ data: [], meta: { total: 0, page: 1, limit: 20 } })
    wrap(<Curation />)
    await waitFor(() => {
      expect(screen.getByText('아직 글이 없어요.')).toBeInTheDocument()
    })
  })

  it('shows error state and retry button on API failure', async () => {
    fetchArticles.mockRejectedValue(new Error('서버 오류'))
    wrap(<Curation />)
    await waitFor(() => {
      expect(screen.getByText('다시 시도')).toBeInTheDocument()
    })
  })
})
