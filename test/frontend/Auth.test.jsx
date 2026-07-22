import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useState } from 'react'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Nav from '@/components/Nav'
import MobileNav from '@/components/MobileNav'
import AuthModal from '@/components/AuthModal'

vi.mock('@/api/client', () => ({ loginMember: vi.fn() }))
import { loginMember } from '@/api/client'

const wrap = (ui) => render(<MemoryRouter>{ui}</MemoryRouter>)

describe('상단 인증 UI', () => {
  beforeEach(() => vi.clearAllMocks())

  it('비로그인 헤더는 시작하기 없이 로그인 버튼 하나만 표시한다', async () => {
    const onLogin = vi.fn()
    const ue = userEvent.setup()
    wrap(<Nav user={null} onLogin={onLogin} />)

    expect(screen.queryByRole('button', { name: '시작하기' })).not.toBeInTheDocument()
    await ue.click(screen.getByRole('button', { name: '로그인' }))
    expect(onLogin).toHaveBeenCalledOnce()
  })

  it('헤더에 검색창을 노출하지 않는다 (검색 기능은 추후 제공)', () => {
    wrap(<Nav user={null} onLogin={vi.fn()} />)
    expect(screen.queryByText('무엇을 배워볼까요?')).not.toBeInTheDocument()
  })

  it('로그인 회원은 닉네임 버튼으로 내 정보 페이지에 이동한다', () => {
    wrap(<Nav user={{ nickname: '재원' }} onLogin={vi.fn()} />)
    expect(screen.getByRole('link', { name: '재원' })).toHaveAttribute('href', '/profile')
    expect(screen.queryByRole('button', { name: '로그인' })).not.toBeInTheDocument()
  })

  it('햄버거는 페이지 이동 대신 모바일 전체 메뉴를 열고 목록 링크를 제공한다', async () => {
    const ue = userEvent.setup()
    wrap(<Nav user={null} onLogin={vi.fn()} onLogout={vi.fn()} />)

    const burger = document.querySelector('.burger')
    expect(burger).toHaveAttribute('aria-label', '전체 메뉴 열기')
    await ue.click(burger)

    const dialog = screen.getByRole('dialog', { name: '모바일 메뉴' })
    const menu = within(dialog)
    expect(menu.getByRole('link', { name: '홈' })).toHaveAttribute('href', '/')
    expect(menu.getByRole('link', { name: '홈' })).toHaveAttribute('aria-current', 'page')
    expect(menu.getByRole('link', { name: '클래스' })).toHaveAttribute('href', '/classes')
    expect(menu.getByRole('link', { name: '큐레이션' })).toHaveAttribute('href', '/curation')
    expect(menu.getByRole('link', { name: '커뮤니티' })).toHaveAttribute('href', '/community')
    expect(menu.getByRole('link', { name: 'meet.pl' })).toHaveAttribute('href', '/meet')
    expect(menu.getByRole('link', { name: 'AI핫딜' })).toHaveAttribute('href', '/hotdeal')
    expect(menu.getAllByRole('button', { name: '모바일 메뉴 닫기' }).at(-1)).toHaveFocus()

    await ue.keyboard('{Escape}')
    expect(screen.queryByRole('dialog', { name: '모바일 메뉴' })).not.toBeInTheDocument()
    expect(burger).toHaveFocus()
    expect(document.body.style.overflow).toBe('')
  })

  it('모바일 메뉴에서 로그인 또는 내 정보·로그아웃을 상태에 맞게 제공한다', async () => {
    const ue = userEvent.setup()
    const onLogin = vi.fn()
    const onLogout = vi.fn()
    const first = wrap(<Nav user={null} onLogin={onLogin} onLogout={onLogout} />)
    const burger = document.querySelector('.burger')
    expect(burger).toHaveAttribute('aria-label', '전체 메뉴 열기')
    await ue.click(burger)
    await ue.click(screen.getByRole('button', { name: '로그인하기' }))
    expect(onLogin).toHaveBeenCalledOnce()
    first.unmount()

    wrap(<Nav user={{ nickname: '재원' }} onLogin={onLogin} onLogout={onLogout} />)
    const burgerLogged = document.querySelector('.burger')
    expect(burgerLogged).toHaveAttribute('aria-label', '전체 메뉴 열기')
    await ue.click(burgerLogged)
    expect(screen.getByRole('link', { name: '재원 내 정보' })).toHaveAttribute('href', '/profile')
    await ue.click(screen.getByRole('button', { name: '로그아웃' }))
    expect(onLogout).toHaveBeenCalledOnce()
  })

  it('현재 경로를 다시 선택해도 메뉴를 닫고 로그아웃 실패는 로그인 상태와 오류를 유지한다', async () => {
    const ue = userEvent.setup()
    const rejectedLogout = vi.fn().mockRejectedValue(new Error('network'))
    const first = render(
      <MemoryRouter initialEntries={['/classes']}>
        <Nav user={null} onLogin={vi.fn()} onLogout={rejectedLogout} />
      </MemoryRouter>,
    )
    await ue.click(first.container.querySelector('.burger'))
    await ue.click(within(screen.getByRole('dialog', { name: '모바일 메뉴' })).getByRole('link', { name: '클래스' }))
    expect(screen.queryByRole('dialog', { name: '모바일 메뉴' })).not.toBeInTheDocument()
    first.unmount()

    render(
      <MemoryRouter><Nav user={{ nickname: '재원' }} onLogin={vi.fn()} onLogout={rejectedLogout} /></MemoryRouter>,
    )
    await ue.click(document.querySelector('.burger'))
    await ue.click(screen.getByRole('button', { name: '로그아웃' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('로그아웃하지 못했습니다')
    expect(screen.getByRole('dialog', { name: '모바일 메뉴' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '재원 내 정보' })).toBeInTheDocument()
  })
})

describe('모바일 하단 메뉴', () => {
  it('MY는 비로그인 시 로그인창을 열고 로그인 시 내 정보로 이동한다', async () => {
    const ue = userEvent.setup()
    const onLogin = vi.fn()
    const first = wrap(<MobileNav user={null} onLogin={onLogin} />)
    await ue.click(screen.getByRole('button', { name: 'MY 로그인' }))
    expect(onLogin).toHaveBeenCalledOnce()
    first.unmount()

    wrap(<MobileNav user={{ nickname: '재원' }} onLogin={onLogin} />)
    expect(screen.getByRole('link', { name: 'MY 내 정보' })).toHaveAttribute('href', '/profile')
  })
})

describe('로그인 모달', () => {
  beforeEach(() => vi.clearAllMocks())

  it('닉네임·비밀번호와 회원가입 안내 버튼을 제공한다', () => {
    wrap(<AuthModal open onClose={vi.fn()} onAuthenticated={vi.fn()} onSignup={vi.fn()} />)
    expect(screen.getByRole('dialog', { name: '로그인' })).toBeInTheDocument()
    expect(screen.getByLabelText('닉네임')).toBeInTheDocument()
    expect(screen.getByLabelText('비밀번호')).toBeInTheDocument()
    expect(screen.getByText('처음이시라면 회원가입을 해주세요')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '회원가입' })).toBeInTheDocument()
    expect(screen.getByLabelText('닉네임')).toHaveFocus()
  })

  it('로그인 모달의 초점을 내부에 가두고 닫으면 호출한 버튼으로 돌려준다', async () => {
    const ue = userEvent.setup()
    function Harness() {
      const [open, setOpen] = useState(false)
      return <><button onClick={() => setOpen(true)}>모달 열기</button><AuthModal open={open} onClose={() => setOpen(false)} onAuthenticated={vi.fn()} onSignup={vi.fn()} /></>
    }
    wrap(<Harness />)
    const trigger = screen.getByRole('button', { name: '모달 열기' })
    await ue.click(trigger)
    const submit = screen.getByRole('button', { name: '로그인' })
    submit.focus()
    await ue.tab()
    expect(screen.getByRole('button', { name: '로그인 창 닫기' })).toHaveFocus()
    await ue.keyboard('{Escape}')
    expect(trigger).toHaveFocus()
  })

  it('로그인 성공 시 서버 회원정보를 전역 상태에 전달한다', async () => {
    const member = { id: 1, nickname: '재원', role: '기획자', interests: ['PM/PO'] }
    loginMember.mockResolvedValue(member)
    const onAuthenticated = vi.fn()
    const ue = userEvent.setup()
    wrap(<AuthModal open onClose={vi.fn()} onAuthenticated={onAuthenticated} onSignup={vi.fn()} />)

    await ue.type(screen.getByLabelText('닉네임'), '재원')
    await ue.type(screen.getByLabelText('비밀번호'), 'Nexus1!pw')
    await ue.click(screen.getByRole('button', { name: '로그인' }))

    expect(loginMember).toHaveBeenCalledWith({ nickname: '재원', password: 'Nexus1!pw' })
    expect(onAuthenticated).toHaveBeenCalledWith(member)
  })

  it('로그인 실패는 모달 안에 표시하고 회원 존재 여부를 노출하지 않는다', async () => {
    loginMember.mockRejectedValue(new Error('닉네임 또는 비밀번호가 올바르지 않습니다'))
    const ue = userEvent.setup()
    wrap(<AuthModal open onClose={vi.fn()} onAuthenticated={vi.fn()} onSignup={vi.fn()} />)

    await ue.type(screen.getByLabelText('닉네임'), '없는회원')
    await ue.type(screen.getByLabelText('비밀번호'), 'Wrong1!pw')
    await ue.click(screen.getByRole('button', { name: '로그인' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('닉네임 또는 비밀번호가 올바르지 않습니다')
  })
})
