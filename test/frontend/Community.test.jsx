import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
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

  it('정의된 커뮤니티 배지를 표시하고 선택한 배지로 서버 필터링한다', async () => {
    wrap(<Community user={null} />)
    await waitFor(() => expect(screen.getByText('RAG 도입 후기')).toBeInTheDocument())

    for (const badge of ['전체', '자료', '노하우', '팁', '기술자료']) {
      expect(screen.getByRole('button', { name: badge })).toBeInTheDocument()
    }
    expect(screen.queryByRole('button', { name: '질문' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '자료' }))
    await waitFor(() => {
      expect(fetchPosts).toHaveBeenLastCalledWith({ tag: '자료', page: 1, size: 20 })
    })
  })

  it('느린 이전 응답이 최신 배지 필터 결과를 덮어쓰지 않는다', async () => {
    const deferred = () => {
      let resolve
      const promise = new Promise(done => { resolve = done })
      return { promise, resolve }
    }
    const allRequest = deferred()
    const tipRequest = deferred()
    fetchPosts
      .mockReset()
      .mockImplementationOnce(() => allRequest.promise)
      .mockImplementationOnce(() => tipRequest.promise)

    wrap(<Community user={null} />)
    await waitFor(() => expect(fetchPosts).toHaveBeenCalledTimes(1))
    fireEvent.click(screen.getByRole('button', { name: '팁' }))
    await waitFor(() => expect(fetchPosts).toHaveBeenCalledTimes(2))

    await act(async () => {
      tipRequest.resolve({
        data: [{ ...mockPostsData.data[0], id: 'tip', tag: '팁', title: '최신 팁 결과' }],
      })
    })
    expect(await screen.findByText('최신 팁 결과')).toBeInTheDocument()

    await act(async () => {
      allRequest.resolve({
        data: [{ ...mockPostsData.data[0], id: 'all', title: '늦은 전체 결과' }],
      })
    })
    expect(screen.getByText('최신 팁 결과')).toBeInTheDocument()
    expect(screen.queryByText('늦은 전체 결과')).not.toBeInTheDocument()
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
