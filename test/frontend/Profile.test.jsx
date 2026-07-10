import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Profile from '@/views/Profile'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('@/api/client', () => ({
  fetchMember: vi.fn(),
  updateMember: vi.fn(),
  deleteMember: vi.fn(),
  registerMember: vi.fn(),
}))

import { fetchMember, updateMember, deleteMember } from '@/api/client'

const mockMember = {
  id: 1,
  nickname: '테스트유저',
  email: 'test@example.com',
  role: '직장인',
  interests: '데이터 분석, LLM·생성형 AI',
  createdAt: '2024-01-15T00:00:00.000Z',
}

const wrap = (ui) => render(<MemoryRouter>{ui}</MemoryRouter>)

describe('Profile', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchMember.mockResolvedValue(mockMember)
  })

  it('renders member fields and shows email as read-only when set', async () => {
    wrap(<Profile user={{ id: 1, nickname: '테스트유저', role: '직장인' }} setUser={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByDisplayValue('테스트유저')).toBeInTheDocument()
    })
    expect(screen.getByText('test@example.com')).toBeInTheDocument()
    expect(screen.getByText('수정 불가')).toBeInTheDocument()
    expect(screen.getByText('2024.01.15')).toBeInTheDocument()
  })

  it('shows email input with hint when email is null', async () => {
    fetchMember.mockResolvedValue({ ...mockMember, email: null })
    wrap(<Profile user={{ id: 1, nickname: '테스트유저', role: '직장인' }} setUser={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText('이메일 입력')).toBeInTheDocument()
    })
    expect(screen.getByText('최초 1회만 등록할 수 있어요')).toBeInTheDocument()
  })

  it('save sends PATCH with only changed fields and updates user', async () => {
    updateMember.mockResolvedValue({ ...mockMember, nickname: '새닉네임' })
    const setUser = vi.fn()
    const ue = userEvent.setup()
    wrap(<Profile user={{ id: 1, nickname: '테스트유저', role: '직장인' }} setUser={setUser} />)

    await waitFor(() => screen.getByDisplayValue('테스트유저'))

    const nicknameInput = screen.getByDisplayValue('테스트유저')
    await ue.clear(nicknameInput)
    await ue.type(nicknameInput, '새닉네임')
    await ue.click(screen.getByText('저장'))

    await waitFor(() => {
      expect(updateMember).toHaveBeenCalledWith(1, { nickname: '새닉네임' })
    })
    expect(setUser).toHaveBeenCalledWith(expect.objectContaining({ nickname: '새닉네임' }))
  })

  it('logout clears user and navigates to /', async () => {
    const setUser = vi.fn()
    const ue = userEvent.setup()
    wrap(<Profile user={{ id: 1, nickname: '테스트유저', role: '직장인' }} setUser={setUser} />)

    await waitFor(() => screen.getByText('로그아웃'))
    await ue.click(screen.getByText('로그아웃'))

    expect(setUser).toHaveBeenCalledWith(null)
    expect(mockNavigate).toHaveBeenCalledWith('/')
  })

  it('withdrawal first click shows warning box but does NOT call deleteMember', async () => {
    const ue = userEvent.setup()
    wrap(<Profile user={{ id: 1, nickname: '테스트유저', role: '직장인' }} setUser={vi.fn()} />)

    await waitFor(() => screen.getByText('탈회'))
    await ue.click(screen.getByText('탈회'))

    expect(screen.getByText('작성한 글과 댓글은 남지만 계정과 좋아요는 삭제됩니다. 되돌릴 수 없습니다.')).toBeInTheDocument()
    expect(screen.getByText('정말 탈회하기')).toBeInTheDocument()
    expect(deleteMember).not.toHaveBeenCalled()
  })

  it('confirming withdrawal calls deleteMember, clears user, navigates to /', async () => {
    deleteMember.mockResolvedValue({ deleted: true })
    const setUser = vi.fn()
    const ue = userEvent.setup()
    wrap(<Profile user={{ id: 1, nickname: '테스트유저', role: '직장인' }} setUser={setUser} />)

    await waitFor(() => screen.getByText('탈회'))
    await ue.click(screen.getByText('탈회'))
    await ue.click(screen.getByText('정말 탈회하기'))

    await waitFor(() => {
      expect(deleteMember).toHaveBeenCalledWith(1)
    })
    expect(setUser).toHaveBeenCalledWith(null)
    expect(mockNavigate).toHaveBeenCalledWith('/')
  })

  it('shows inline error message on save failure without using alert', async () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    updateMember.mockRejectedValue(new Error('닉네임 중복'))
    const ue = userEvent.setup()
    wrap(<Profile user={{ id: 1, nickname: '테스트유저', role: '직장인' }} setUser={vi.fn()} />)

    await waitFor(() => screen.getByDisplayValue('테스트유저'))

    const nicknameInput = screen.getByDisplayValue('테스트유저')
    await ue.clear(nicknameInput)
    await ue.type(nicknameInput, '중복닉네임')
    await ue.click(screen.getByText('저장'))

    await waitFor(() => {
      expect(screen.getByText('닉네임 중복')).toBeInTheDocument()
    })
    expect(alertSpy).not.toHaveBeenCalled()
    alertSpy.mockRestore()
  })
})
