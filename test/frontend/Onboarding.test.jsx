import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import Onboarding from '@/views/Onboarding'
import { passwordMissing } from '@/utils/password'

vi.mock('@/api/client', () => ({ checkNickname: vi.fn() }))
import { checkNickname } from '@/api/client'

const INTERESTS = [
  '서비스기획', 'PM/PO', '사업전략', '데이터분석', 'UX', '마케팅/그로스', '서비스운영',
  '프론트엔드', '백엔드', 'AI/ML', '모바일', '인프라', 'DevOps', 'QA', '보안',
]

const wrap = (onFinish = vi.fn().mockResolvedValue({ nickname: '신규회원' })) => render(
  <MemoryRouter initialEntries={['/onboarding']}>
    <Routes>
      <Route path="/onboarding" element={<Onboarding onFinish={onFinish} />} />
      <Route path="/" element={<p>홈 화면</p>} />
    </Routes>
  </MemoryRouter>,
)

async function fillCredentials(ue, nickname = '신규회원', password = 'Abcdef1!') {
  await ue.type(screen.getByLabelText('닉네임'), nickname)
  await ue.type(screen.getByLabelText('비밀번호'), password)
  await ue.click(screen.getByRole('button', { name: '중복 확인' }))
  await ue.click(screen.getByRole('radio', { name: '기획자' }))
}

async function goToInterests(ue) {
  await fillCredentials(ue)
  await ue.click(screen.getByRole('button', { name: '다음' }))
}

describe('passwordMissing — 정책 규칙 (영문·숫자 포함 8자 이상, 특수문자는 선택)', () => {
  it.each([
    ['Ab1!', ['8자 이상']], ['12345678!', ['영문']], ['abcdefgh!', ['숫자']],
    ['abcdef12', []], ['Abcdef1!', []],
  ])('%s → 부족: %j', (pw, expected) => expect(passwordMissing(pw)).toEqual(expected))
})

describe('회원가입 온보딩', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    checkNickname.mockResolvedValue({ nickname: '신규회원', available: true })
  })

  it('닉네임 중복확인, 비밀번호 정책, 기획자·개발자 역할을 제공한다', () => {
    wrap()
    expect(screen.getByRole('button', { name: '중복 확인' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: '기획자' })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: '개발자' })).toBeInTheDocument()
    expect(screen.queryByRole('radio', { name: '직장인' })).not.toBeInTheDocument()
    expect(screen.getByPlaceholderText(/영문·숫자 포함 8자 이상/)).toBeInTheDocument()
  })

  it('중복 닉네임을 차단하고 닉네임 변경 시 확인 상태를 초기화한다', async () => {
    checkNickname.mockResolvedValueOnce({ nickname: '중복회원', available: false })
    const ue = userEvent.setup()
    wrap()
    await ue.type(screen.getByLabelText('닉네임'), '중복회원')
    await ue.click(screen.getByRole('button', { name: '중복 확인' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('이미 사용 중')

    await ue.type(screen.getByLabelText('닉네임'), '2')
    expect(screen.queryByText('사용 가능한 닉네임입니다')).not.toBeInTheDocument()
  })

  it('약한 비밀번호 또는 중복확인·역할 누락 시 다음 단계로 가지 않는다', async () => {
    const ue = userEvent.setup()
    wrap()
    await ue.type(screen.getByLabelText('닉네임'), '테스터')
    await ue.type(screen.getByLabelText('비밀번호'), 'weak')
    await ue.click(screen.getByRole('button', { name: '다음' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('숫자')
    expect(screen.getByLabelText('비밀번호')).toBeInTheDocument()
  })

  it('관심사를 정확한 15개 유형으로 제공하고 한 건 이상 선택해야 한다', async () => {
    const ue = userEvent.setup()
    wrap()
    await goToInterests(ue)
    for (const interest of INTERESTS) {
      expect(screen.getByRole('button', { name: interest })).toBeInTheDocument()
    }
    await ue.click(screen.getByRole('button', { name: '다음' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('한 개 이상')
  })

  it('역할과 복수 관심사를 확인 화면에서 하이라이트한다', async () => {
    const ue = userEvent.setup()
    wrap()
    await goToInterests(ue)
    await ue.click(screen.getByRole('button', { name: 'PM/PO' }))
    await ue.click(screen.getByRole('button', { name: 'AI/ML' }))
    await ue.click(screen.getByRole('button', { name: '다음' }))

    expect(screen.getByText('가입 정보를 확인해 주세요')).toBeInTheDocument()
    expect(screen.getByText('기획자')).toBeInTheDocument()
    expect(screen.getByText('PM/PO')).toBeInTheDocument()
    expect(screen.getByText('AI/ML')).toBeInTheDocument()
  })

  it('회원가입 완료 후 축하 메시지와 홈으로 가기 버튼을 제공한다', async () => {
    const onFinish = vi.fn().mockResolvedValue({ nickname: '신규회원' })
    const ue = userEvent.setup()
    wrap(onFinish)
    await goToInterests(ue)
    await ue.click(screen.getByRole('button', { name: '서비스기획' }))
    await ue.click(screen.getByRole('button', { name: '다음' }))
    await ue.click(screen.getByRole('button', { name: '회원가입' }))

    expect(await screen.findByText('회원가입을 축하합니다!')).toBeInTheDocument()
    expect(onFinish).toHaveBeenCalledWith({
      name: '신규회원', password: 'Abcdef1!', role: '기획자', interests: ['서비스기획'],
    })
    await ue.click(screen.getByRole('button', { name: '홈으로 가기' }))
    expect(await screen.findByText('홈 화면')).toBeInTheDocument()
  })
})
