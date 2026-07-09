import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Community from '@/views/Community'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('@/api/client', () => ({
  fetchPosts: vi.fn(),
}))

import { fetchPosts } from '@/api/client'

const mockPostsData = {
  data: [
    {
      id: 'p1',
      tag: '노하우',
      title: 'RAG 도입 후기',
      authorName: '데브워커',
      likesCount: 218,
      commentsCount: 3,
      createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: 'p2',
      tag: '기술자료',
      title: 'gemma 27B 로컬 구동 스펙',
      authorName: 'GPU장인',
      likesCount: 312,
      commentsCount: 2,
      createdAt: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(),
    },
  ],
  meta: { total: 2, page: 1, limit: 20 },
}

const wrap = (ui) => render(<MemoryRouter>{ui}</MemoryRouter>)

describe('Community list', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchPosts.mockResolvedValue(mockPostsData)
  })

  it('renders post titles from mock API', async () => {
    wrap(<Community user={null} />)
    await waitFor(() => {
      expect(screen.getByText('RAG 도입 후기')).toBeInTheDocument()
    })
    expect(screen.getByText('gemma 27B 로컬 구동 스펙')).toBeInTheDocument()
  })

  it('글쓰기 button navigates to /community/write when user is an object', async () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    wrap(<Community user={{ id: 1, nickname: '테스트유저', role: '직장인' }} />)
    await waitFor(() => screen.getByText('✎ 글쓰기'))
    fireEvent.click(screen.getByText('✎ 글쓰기'))
    expect(mockNavigate).toHaveBeenCalledWith('/community/write')
    expect(alertSpy).not.toHaveBeenCalled()
    alertSpy.mockRestore()
  })

  it('글쓰기 button navigates to /community/write when user is a legacy string', async () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    wrap(<Community user="김크레딧" />)
    await waitFor(() => screen.getByText('✎ 글쓰기'))
    fireEvent.click(screen.getByText('✎ 글쓰기'))
    expect(mockNavigate).toHaveBeenCalledWith('/community/write')
    expect(alertSpy).not.toHaveBeenCalled()
    alertSpy.mockRestore()
  })

  it('글쓰기 button navigates to /onboarding when no user', async () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    wrap(<Community user={null} />)
    await waitFor(() => screen.getByText('✎ 글쓰기'))
    fireEvent.click(screen.getByText('✎ 글쓰기'))
    expect(mockNavigate).toHaveBeenCalledWith('/onboarding')
    expect(alertSpy).not.toHaveBeenCalled()
    alertSpy.mockRestore()
  })

  it('window.alert is never called when 글쓰기 is clicked regardless of auth state', async () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    wrap(<Community user={null} />)
    await waitFor(() => screen.getByText('✎ 글쓰기'))
    fireEvent.click(screen.getByText('✎ 글쓰기'))
    expect(alertSpy).not.toHaveBeenCalled()
    alertSpy.mockRestore()
  })
})
