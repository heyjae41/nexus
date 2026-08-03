import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import CardPick from '@/views/CardPick'

vi.mock('@/api/client', () => ({
  fetchCardBenefits: vi.fn(),
}))

import { fetchCardBenefits } from '@/api/client'

const benefits = [
  {
    id: 1,
    title: '해외 결제하면 최대 10만 하나머니!',
    event_period: '2026.08.01 ~ 2026.09.30',
    card_company: '하나카드',
    target_cards: 'JADE 카드 (Visa 브랜드)',
    benefit_tags: ['적립', '캐시백'],
    detail_url: 'https://m.hanacard.co.kr/MKEVT1010M.web?EVN_SEQ=60480&ref=nexus.bccard.ai',
    image_url: 'https://m.hanacard.co.kr/a.png',
  },
  {
    id: 2,
    title: 'WON트래블 호텔 최대 25% 할인',
    event_period: '2026.08.01 ~ 2026.08.31',
    card_company: '우리카드',
    target_cards: '우리카드 개인 신용/체크',
    benefit_tags: ['할인'],
    detail_url: 'https://m.wooricard.com/dcmw/yh1/bnf/bnf02/prgevnt/movePrgEvntDtl.do?evntSrno=30006146&ref=nexus.bccard.ai',
    image_url: null,
  },
]

function renderView() {
  return render(
    <MemoryRouter>
      <CardPick />
    </MemoryRouter>,
  )
}

describe('CardPick 뷰', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchCardBenefits.mockResolvedValue(benefits)
  })

  it('카드 혜택 목록을 필수 정보와 함께 렌더한다', async () => {
    renderView()
    expect(await screen.findByText('해외 결제하면 최대 10만 하나머니!')).toBeInTheDocument()
    expect(screen.getByText('WON트래블 호텔 최대 25% 할인')).toBeInTheDocument()
    expect(screen.getByText('2026.08.01 ~ 2026.09.30')).toBeInTheDocument()
    expect(screen.getByText(/JADE 카드/)).toBeInTheDocument()

    const link = screen.getAllByTestId('cardpick-card-link')[0]
    expect(link).toHaveAttribute('target', '_blank')
    expect(link.getAttribute('href')).toContain('ref=nexus.bccard.ai')
  })

  it('카드사 필터가 동작한다', async () => {
    renderView()
    await screen.findByText('WON트래블 호텔 최대 25% 할인')

    fireEvent.click(screen.getByRole('button', { name: '우리카드' }))
    expect(screen.queryByText('해외 결제하면 최대 10만 하나머니!')).not.toBeInTheDocument()
    expect(screen.getByText('WON트래블 호텔 최대 25% 할인')).toBeInTheDocument()
  })

  it('로딩 실패 시 재시도 UI 를 보여준다 (browser dialog 금지)', async () => {
    fetchCardBenefits.mockRejectedValueOnce(new Error('네트워크 오류'))
    renderView()
    expect(await screen.findByRole('alert')).toHaveTextContent('불러오지 못했습니다')
    fetchCardBenefits.mockResolvedValueOnce(benefits)
    fireEvent.click(screen.getByRole('button', { name: '다시 시도' }))
    expect(await screen.findByText('WON트래블 호텔 최대 25% 할인')).toBeInTheDocument()
  })

  it('빈 목록이면 안내 문구를 보여준다', async () => {
    fetchCardBenefits.mockResolvedValueOnce([])
    renderView()
    expect(await screen.findByText('진행 중인 혜택이 없습니다.')).toBeInTheDocument()
  })
})
