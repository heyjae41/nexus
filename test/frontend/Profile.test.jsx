import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { mockNavigate } from './helpers'
import { MemoryRouter } from 'react-router-dom'
import Profile from '@/views/Profile'

vi.mock('@/api/client', () => ({
  fetchCurrentMember: vi.fn(), updateCurrentMember: vi.fn(),
  logoutMember: vi.fn(), deleteCurrentMember: vi.fn(),
}))
import { fetchCurrentMember, updateCurrentMember, logoutMember, deleteCurrentMember } from '@/api/client'

const member = {
  id: 1, nickname: '테스트유저', role: '기획자',
  interests: ['서비스기획', 'PM/PO'], createdAt: '2024-01-15T00:00:00.000Z',
}
const wrap = setUser => render(<MemoryRouter><Profile user={member} setUser={setUser || vi.fn()} /></MemoryRouter>)

describe('내 정보', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchCurrentMember.mockResolvedValue(member)
    logoutMember.mockResolvedValue({ loggedOut: true })
  })

  it('선택된 역할과 복수 관심사를 하이라이트한다', async () => {
    wrap()
    await screen.findByText('내 정보')
    expect(screen.getByRole('button', { name: '기획자' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: '개발자' })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('button', { name: '서비스기획' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'PM/PO' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: '보안' })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByText('2024.01.15')).toBeInTheDocument()
  })

  it('역할과 여러 관심사를 수정해 저장하고 상단 회원 상태를 갱신한다', async () => {
    const updated = { ...member, role: '개발자', interests: ['서비스기획', '백엔드', 'AI/ML'] }
    updateCurrentMember.mockResolvedValue(updated)
    const setUser = vi.fn()
    const ue = userEvent.setup()
    wrap(setUser)
    await screen.findByText('내 정보')

    await ue.click(screen.getByRole('button', { name: '개발자' }))
    await ue.click(screen.getByRole('button', { name: 'PM/PO' }))
    await ue.click(screen.getByRole('button', { name: '백엔드' }))
    await ue.click(screen.getByRole('button', { name: 'AI/ML' }))
    await ue.click(screen.getByRole('button', { name: '저장' }))

    expect(updateCurrentMember).toHaveBeenCalledWith({
      role: '개발자', interests: ['서비스기획', '백엔드', 'AI/ML'],
    })
    expect(setUser).toHaveBeenCalledWith(updated)
    expect(await screen.findByText('저장되었습니다.')).toBeInTheDocument()
  })

  it('관심사를 모두 해제하면 저장하지 않고 한 건 이상 선택을 안내한다', async () => {
    const ue = userEvent.setup()
    wrap()
    await screen.findByText('내 정보')
    await ue.click(screen.getByRole('button', { name: '서비스기획' }))
    await ue.click(screen.getByRole('button', { name: 'PM/PO' }))
    await ue.click(screen.getByRole('button', { name: '저장' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('한 개 이상')
    expect(updateCurrentMember).not.toHaveBeenCalled()
  })

  it('로그아웃은 서버 세션과 전역 사용자를 지우고 홈으로 이동한다', async () => {
    const setUser = vi.fn()
    const ue = userEvent.setup()
    wrap(setUser)
    await screen.findByText('로그아웃')
    await ue.click(screen.getByRole('button', { name: '로그아웃' }))
    await waitFor(() => expect(logoutMember).toHaveBeenCalledOnce())
    expect(setUser).toHaveBeenCalledWith(null)
    expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true })
  })

  it('탈회 확인 시 서버 회원정보를 삭제하고 로그인 상태를 지운다', async () => {
    deleteCurrentMember.mockResolvedValue({ deleted: true })
    const setUser = vi.fn()
    const ue = userEvent.setup()
    wrap(setUser)
    await screen.findByText('탈회')
    await ue.click(screen.getByRole('button', { name: '탈회' }))
    expect(deleteCurrentMember).not.toHaveBeenCalled()
    await ue.click(screen.getByRole('button', { name: '정말 탈회하기' }))
    await waitFor(() => expect(deleteCurrentMember).toHaveBeenCalledOnce())
    expect(setUser).toHaveBeenCalledWith(null)
    expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true })
  })
})
