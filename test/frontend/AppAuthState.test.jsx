import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('@/views/Home', () => ({ default: () => <main>홈 콘텐츠</main> }))
vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    fetchCurrentMember: vi.fn(), registerAccount: vi.fn(), loginMember: vi.fn(),
  }
})
import { fetchCurrentMember, loginMember } from '@/api/client'
import App from '@/App'

describe('앱 로그인 세션 상태', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.history.replaceState({}, '', '/')
    localStorage.removeItem('nexus.user')
  })

  it('새로고침 시 서버 세션의 현재 회원을 복원해 닉네임을 표시한다', async () => {
    fetchCurrentMember.mockResolvedValue({ id: 1, nickname: '세션회원', role: '기획자', interests: ['PM/PO'] })
    render(<App />)
    expect(await screen.findByRole('link', { name: '세션회원' })).toHaveAttribute('href', '/profile')
    expect(screen.queryByRole('button', { name: '로그인' })).not.toBeInTheDocument()
  })

  it('세션이 없으면 로그인 버튼을 표시하고 로그인 성공 즉시 닉네임으로 바꾼다', async () => {
    fetchCurrentMember.mockRejectedValue(new Error('로그인이 필요합니다'))
    loginMember.mockResolvedValue({ id: 2, nickname: '로그인회원', role: '개발자', interests: ['백엔드'] })
    const ue = userEvent.setup()
    render(<App />)

    await ue.click(await screen.findByRole('button', { name: '로그인' }))
    await ue.type(screen.getByLabelText('닉네임'), '로그인회원')
    await ue.type(screen.getByLabelText('비밀번호'), 'Nexus1!pw')
    await ue.click(screen.getByRole('dialog').querySelector('button[type="submit"]'))

    await waitFor(() => expect(screen.getByRole('link', { name: '로그인회원' })).toBeInTheDocument())
  })
})
