import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Classes from '@/views/Classes'

vi.mock('@/api/client', () => ({ fetchClasses: vi.fn() }))
import { fetchClasses } from '@/api/client'

const course = {
  id: 1, sourceId: '264403', title: 'AI 투자 에이전트', summary: '설명',
  sourceCategoryName: 'AI TECH', category: 'RAG & AI Agent', formatName: '올인원',
  qualification: '누구나', runningTimeMinutes: 1200, price: 239000, original: 400000,
  badges: ['BEST', 'NEW', '인기 급상승'], coverImageUrl: 'https://cdn.example/a.webp',
  linkUrl: 'https://fastcampus.co.kr/data_online_aistock?ref=nexus.bccard.ai', isExternal: true,
}

const wrap = () => render(<BrowserRouter><Classes /></BrowserRouter>)

describe('Classes — 수집형 목록', () => {
  beforeEach(() => vi.clearAllMocks())

  it('API 과정과 대상 태그를 표시하고 외부 링크로 이동한다', async () => {
    fetchClasses.mockResolvedValue({ data: [course], meta: { total: 1, page: 1, limit: 20 } })
    wrap()
    expect(await screen.findByText('AI 투자 에이전트')).toBeInTheDocument()
    for (const badge of ['BEST', 'NEW', '인기 급상승']) expect(screen.getByText(badge)).toBeInTheDocument()
    const card = screen.getByTestId('class-card-external')
    expect(card).toHaveAttribute('href', course.linkUrl)
    expect(card).toHaveAttribute('target', '_blank')
  })

  it('세 수집 카테고리를 서버 필터로 전달한다', async () => {
    fetchClasses.mockResolvedValue({ data: [course], meta: { total: 1, page: 1, limit: 20 } })
    wrap()
    await screen.findByText('AI 투자 에이전트')
    for (const label of ['전체', 'AI TECH', 'AI CREATIVE', 'AI/업무생산성']) {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument()
    }
    fireEvent.click(screen.getByRole('button', { name: 'AI CREATIVE' }))
    await waitFor(() => expect(fetchClasses).toHaveBeenLastCalledWith({ category: 'AICREATIVE', page: 1, size: 20 }))
  })

  it('빈 결과를 안내한다', async () => {
    fetchClasses.mockResolvedValueOnce({ data: [], meta: { total: 0, page: 1, limit: 20 } })
    wrap()
    expect(await screen.findByText('조건에 맞는 클래스가 없어요.')).toBeInTheDocument()
  })

  it('오류를 알리고 다시 시도한다', async () => {
    fetchClasses
      .mockRejectedValueOnce(new Error('서버 오류'))
      .mockResolvedValueOnce({ data: [course], meta: { total: 1, page: 1, limit: 20 } })
    wrap()
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('서버 오류')
    fireEvent.click(screen.getByRole('button', { name: '다시 시도' }))
    expect(await screen.findByText('AI 투자 에이전트')).toBeInTheDocument()
    expect(fetchClasses).toHaveBeenCalledTimes(2)
  })
})
