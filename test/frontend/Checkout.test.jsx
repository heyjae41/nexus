/**
 * Checkout — 결제 완료가 로그인 세션을 파괴하지 않아야 한다.
 *
 * 회귀 배경: doPay() → onPay('김크레딧') → App.finishOnboarding 이 문자열 경로에서
 * 무조건 registerMember 를 호출해, 로그인된 사용자의 세션(localStorage nexus.user)을
 * 익명 신규 회원으로 덮어쓰는 버그가 있었다.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import App from '@/App'

vi.mock('@/api/client', () => ({
  fetchHome: vi.fn().mockResolvedValue({ sections: [] }),
  fetchArticles: vi.fn().mockResolvedValue({ data: [] }),
  fetchArticle: vi.fn().mockResolvedValue({}),
  likeArticle: vi.fn().mockResolvedValue({}),
  fetchEvents: vi.fn().mockResolvedValue({ data: [] }),
  fetchCurrentMember: vi.fn(),
  registerAccount: vi.fn(),
  loginMember: vi.fn(),
  registerMember: vi.fn().mockResolvedValue({ id: 99, nickname: '김크레딧', role: null }),
  fetchMember: vi.fn().mockResolvedValue({}),
  updateMember: vi.fn().mockResolvedValue({}),
  deleteMember: vi.fn().mockResolvedValue({}),
  fetchPosts: vi.fn().mockResolvedValue({ data: [] }),
  fetchPost: vi.fn().mockResolvedValue({}),
  createPost: vi.fn().mockResolvedValue({}),
  createComment: vi.fn().mockResolvedValue({}),
  likePost: vi.fn().mockResolvedValue({}),
}))

import { fetchCurrentMember, registerMember } from '@/api/client'

async function payAndExpectNoRegister() {
  render(<App />)
  fireEvent.click(await screen.findByRole('button', { name: /결제하기/ }))
  await screen.findByText('수강 신청 완료!')
  expect(registerMember).not.toHaveBeenCalled()
}

describe('Checkout — 결제와 로그인 세션', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    window.history.pushState({}, '', '/checkout/c1')
  })

  it('로그인된 사용자가 결제해도 세션을 덮어쓰지 않는다 (신규 가입 없음)', async () => {
    const existing = { id: 7, nickname: '실사용자', role: '개발자' }
    fetchCurrentMember.mockResolvedValue(existing)

    await payAndExpectNoRegister()
    expect(screen.getByRole('link', { name: '실사용자' })).toBeInTheDocument()
    expect(localStorage.getItem('nexus.user')).toBeNull()
  })

  it('비로그인 결제는 게스트 계정을 만들지 않는다 (비밀번호 정책)', async () => {
    fetchCurrentMember.mockRejectedValue(new Error('로그인이 필요합니다'))
    await payAndExpectNoRegister()
    expect(localStorage.getItem('nexus.user')).toBeNull()
  })

  it('비로그인 사용자의 수강 신청은 온보딩으로 유도한다', async () => {
    fetchCurrentMember.mockRejectedValue(new Error('로그인이 필요합니다'))
    window.history.pushState({}, '', '/classes/c1')
    render(<App />)

    fireEvent.click(await screen.findByRole('button', { name: /수강 신청하기/ }))
    await waitFor(() => {
      expect(window.location.pathname).toBe('/onboarding')
    })
    expect(registerMember).not.toHaveBeenCalled()
  })
})
