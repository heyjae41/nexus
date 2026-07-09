import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import CommunityWrite from '@/views/CommunityWrite'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('@/api/client', () => ({
  createPost: vi.fn(),
  registerMember: vi.fn(),
}))

import { createPost, registerMember } from '@/api/client'

const wrap = (ui) => render(<MemoryRouter>{ui}</MemoryRouter>)

describe('CommunityWrite', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('redirects to /onboarding when no user', () => {
    wrap(<CommunityWrite user={null} setUser={vi.fn()} />)
    expect(mockNavigate).toHaveBeenCalledWith('/onboarding', { replace: true })
  })

  it('renders form fields when user is logged in', () => {
    wrap(<CommunityWrite user={{ id: 1, nickname: '테스트유저' }} setUser={vi.fn()} />)
    expect(screen.getByPlaceholderText('제목을 입력해주세요')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('본문을 입력해주세요')).toBeInTheDocument()
    expect(screen.getByText('등록')).toBeInTheDocument()
  })

  it('renders all 5 allowed tag chips', () => {
    wrap(<CommunityWrite user={{ id: 1, nickname: '테스트유저' }} setUser={vi.fn()} />)
    for (const tag of ['노하우', '기술자료', '팁', '자료', '질문']) {
      expect(screen.getByText(tag)).toBeInTheDocument()
    }
  })

  it('submits post with correct payload and navigates to the new post', async () => {
    createPost.mockResolvedValue({ id: 'new-post-1', title: '테스트 제목' })
    const ue = userEvent.setup()
    wrap(<CommunityWrite user={{ id: 1, nickname: '테스트유저' }} setUser={vi.fn()} />)

    await ue.click(screen.getByText('팁'))
    await ue.type(screen.getByPlaceholderText('제목을 입력해주세요'), '테스트 제목')
    await ue.type(screen.getByPlaceholderText('본문을 입력해주세요'), '테스트 본문')
    await ue.click(screen.getByText('등록'))

    await waitFor(() => {
      expect(createPost).toHaveBeenCalledWith({
        memberId: 1,
        tag: '팁',
        title: '테스트 제목',
        body: '테스트 본문',
      })
    })
    expect(mockNavigate).toHaveBeenCalledWith('/community/new-post-1')
  })

  it('shows inline error on API failure without using alert', async () => {
    createPost.mockRejectedValue(new Error('서버 오류입니다'))
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    const ue = userEvent.setup()
    wrap(<CommunityWrite user={{ id: 1, nickname: '테스트유저' }} setUser={vi.fn()} />)

    await ue.type(screen.getByPlaceholderText('제목을 입력해주세요'), '제목')
    await ue.type(screen.getByPlaceholderText('본문을 입력해주세요'), '본문')
    await ue.click(screen.getByText('등록'))

    await waitFor(() => {
      expect(screen.getByText('서버 오류입니다')).toBeInTheDocument()
    })
    expect(alertSpy).not.toHaveBeenCalled()
    alertSpy.mockRestore()
  })

  it('auto-migrates legacy string user before submitting', async () => {
    registerMember.mockResolvedValue({ id: 99, nickname: '김크레딧', role: null })
    createPost.mockResolvedValue({ id: 'post-legacy', title: '글' })
    const setUser = vi.fn()
    const ue = userEvent.setup()
    wrap(<CommunityWrite user="김크레딧" setUser={setUser} />)

    await ue.type(screen.getByPlaceholderText('제목을 입력해주세요'), '글 제목')
    await ue.type(screen.getByPlaceholderText('본문을 입력해주세요'), '글 본문')
    await ue.click(screen.getByText('등록'))

    await waitFor(() => {
      expect(registerMember).toHaveBeenCalledWith({ nickname: '김크레딧' })
    })
    expect(setUser).toHaveBeenCalledWith({ id: 99, nickname: '김크레딧', role: null })
    expect(createPost).toHaveBeenCalledWith(expect.objectContaining({ memberId: 99 }))
    expect(mockNavigate).toHaveBeenCalledWith('/community/post-legacy')
  })
})
