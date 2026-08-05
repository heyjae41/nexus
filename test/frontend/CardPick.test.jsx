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
    benefit_summary: '해외 결제 시 최대 10만 하나머니 적립',
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

const countryFacets = [
  { name: '일본', flag: '🇯🇵', count: 2 },
  { name: '베트남', flag: '🇻🇳', count: 3 },
  { name: '해외공통', flag: '🌏', count: 1 },
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
    fetchCardBenefits.mockResolvedValue({ items: benefits, countries: countryFacets })
  })

  it('카드 혜택 목록을 필수 정보와 함께 렌더한다', async () => {
    renderView()
    expect(await screen.findByText('해외 결제하면 최대 10만 하나머니!')).toBeInTheDocument()
    expect(screen.getByText('WON트래블 호텔 최대 25% 할인')).toBeInTheDocument()
    expect(screen.getByText('2026.08.01 ~ 2026.09.30')).toBeInTheDocument()
    expect(screen.getByText(/JADE 카드/)).toBeInTheDocument()
    // 제목 아래 이벤트 혜택 요약
    expect(screen.getByText('해외 결제 시 최대 10만 하나머니 적립')).toBeInTheDocument()

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

  it('카드사 필터 버튼은 데이터에 있는 카드사로 동적 생성된다', async () => {
    fetchCardBenefits.mockResolvedValueOnce({ items: [
      ...benefits,
      { id: 3, title: '신한 여행 이벤트', event_period: '2026.08.01 ~', card_company: '신한카드',
        target_cards: null, benefit_summary: null, benefit_tags: [], detail_url: 'https://ex.com/3', image_url: null },
    ], countries: countryFacets })
    renderView()
    await screen.findByText('신한 여행 이벤트')
    // 데이터에 있는 카드사(하나/우리/신한) 버튼이 모두 노출
    expect(screen.getByRole('button', { name: '하나카드' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '우리카드' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '신한카드' })).toBeInTheDocument()
  })

  it('로딩 실패 시 재시도 UI 를 보여준다 (browser dialog 금지)', async () => {
    fetchCardBenefits.mockRejectedValueOnce(new Error('네트워크 오류'))
    renderView()
    expect(await screen.findByRole('alert')).toHaveTextContent('불러오지 못했습니다')
    fetchCardBenefits.mockResolvedValueOnce({ items: benefits, countries: countryFacets })
    fireEvent.click(screen.getByRole('button', { name: '다시 시도' }))
    expect(await screen.findByText('WON트래블 호텔 최대 25% 할인')).toBeInTheDocument()
  })

  it('빈 목록이면 안내 문구를 보여준다', async () => {
    fetchCardBenefits.mockResolvedValueOnce({ items: [], countries: [] })
    renderView()
    expect(await screen.findByText('진행 중인 혜택이 없습니다.')).toBeInTheDocument()
  })


  it('국가 필터 칩이 집계 데이터로 렌더되고 클릭 시 country 로 재조회한다', async () => {
    renderView()
    await screen.findByText('WON트래블 호텔 최대 25% 할인')
    const chip = screen.getByRole('button', { name: /베트남/ })
    expect(chip).toHaveTextContent('3')  // 전개 건수 표시

    fetchCardBenefits.mockResolvedValueOnce({ items: [benefits[1]], countries: countryFacets })
    fireEvent.click(chip)
    await waitFor(() => {
      expect(fetchCardBenefits).toHaveBeenLastCalledWith(
        expect.objectContaining({ country: '베트남' }),
      )
    })
  })
})

