/**
 * Tests for Meet view — events rendered from mocked /api/events
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Meet from '@/views/Meet'

vi.mock('@/api/client', () => ({
  fetchEvents: vi.fn(),
}))

import { fetchEvents } from '@/api/client'
import { deferred } from './helpers'

function makeEvent(i) {
  return {
    id: `ev-${i}`,
    title: `테스트 이벤트 ${i}`,
    hostName: `호스트 ${i}`,
    eventStart: `2026-07-${String(i + 10).padStart(2, '0')}T18:30:00`,
    eventEnd: `2026-07-${String(i + 10).padStart(2, '0')}T21:00:00`,
    place: `장소 ${i}`,
    area: `지역 ${i}`,
    priceText: i % 2 === 0 ? '무료' : '15,000원~',
    viewCount: i * 100,
    eventSystemType: i % 3 === 0 ? 'online' : 'offline',
    category: `카테고리 ${i}`,
    coverImageUrl: null,
    linkUrl: `https://event-us.kr/event/${i}?ref=nexus.bccard.ai`,
    isExternal: true,
  }
}

const wrap = (ui) => render(<BrowserRouter>{ui}</BrowserRouter>)

async function renderAndWaitForEvent(label) {
  wrap(<Meet />)
  await waitFor(() => {
    expect(screen.getByText(label)).toBeInTheDocument()
  })
}

describe('Meet view — events from API', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders event cards from mocked /api/events', async () => {
    fetchEvents.mockResolvedValue({
      data: [makeEvent(1), makeEvent(2), makeEvent(3)],
      meta: { total: 3, page: 1, limit: 20 },
    })
    await renderAndWaitForEvent('테스트 이벤트 1')
    expect(screen.getByText('테스트 이벤트 2')).toBeInTheDocument()
    expect(screen.getByText('테스트 이벤트 3')).toBeInTheDocument()
  })

  it('5페이지에서 수집한 이벤트 배지를 표시하고 선택한 배지로 서버 필터링한다', async () => {
    fetchEvents.mockResolvedValue({
      data: [makeEvent(1)],
      meta: { total: 1, page: 1, limit: 20 },
    })
    wrap(<Meet />)
    await waitFor(() => expect(screen.getByText('테스트 이벤트 1')).toBeInTheDocument())

    for (const badge of ['전체', 'IT/프로그래밍', 'AI', '경제/금융']) {
      expect(screen.getByRole('button', { name: badge })).toBeInTheDocument()
    }
    expect(screen.getByRole('button', { name: '전체' })).toHaveAttribute('aria-pressed', 'true')

    fireEvent.click(screen.getByRole('button', { name: '경제/금융' }))
    await waitFor(() => {
      expect(fetchEvents).toHaveBeenLastCalledWith({
        category: '경제/금융', page: 1, size: 20,
      })
    })
    expect(screen.getByRole('button', { name: '경제/금융' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: '전체' })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('group', { name: '이벤트 배지 필터' })).toBeInTheDocument()
  })

  it('선택한 배지를 페이지 2에서도 유지하고 현재 페이지를 보조기술에 알린다', async () => {
    fetchEvents.mockResolvedValue({
      data: [makeEvent(1)],
      meta: { total: 25, page: 1, limit: 20 },
    })
    wrap(<Meet />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'AI' })).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: 'AI' }))
    await waitFor(() => expect(fetchEvents).toHaveBeenLastCalledWith({ category: 'AI', page: 1, size: 20 }))

    const pagination = screen.getByRole('navigation', { name: '이벤트 페이지' })
    expect(pagination).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '1' })).toHaveAttribute('aria-current', 'page')

    fireEvent.click(screen.getByRole('button', { name: '2' }))
    await waitFor(() => expect(fetchEvents).toHaveBeenLastCalledWith({ category: 'AI', page: 2, size: 20 }))
    expect(screen.getByRole('button', { name: '2' })).toHaveAttribute('aria-current', 'page')
  })

  it('느린 이전 응답이 최신 이벤트 배지 결과를 덮어쓰지 않는다', async () => {
    const allRequest = deferred()
    const aiRequest = deferred()
    fetchEvents
      .mockImplementationOnce(() => allRequest.promise)
      .mockImplementationOnce(() => aiRequest.promise)

    wrap(<Meet />)
    await waitFor(() => expect(fetchEvents).toHaveBeenCalledTimes(1))
    fireEvent.click(screen.getByRole('button', { name: 'AI' }))
    await waitFor(() => expect(fetchEvents).toHaveBeenCalledTimes(2))

    await act(async () => {
      aiRequest.resolve({
        data: [{ ...makeEvent(2), title: '최신 AI 이벤트', category: 'AI' }],
        meta: { total: 1, page: 1, limit: 20 },
      })
    })
    expect(await screen.findByText('최신 AI 이벤트')).toBeInTheDocument()

    await act(async () => {
      allRequest.resolve({
        data: [{ ...makeEvent(1), title: '늦은 전체 이벤트' }],
        meta: { total: 1, page: 1, limit: 20 },
      })
    })
    expect(screen.getByText('최신 AI 이벤트')).toBeInTheDocument()
    expect(screen.queryByText('늦은 전체 이벤트')).not.toBeInTheDocument()
  })

  it('each card is an <a> with target="_blank" and the linkUrl', async () => {
    fetchEvents.mockResolvedValue({
      data: [makeEvent(1), makeEvent(2)],
      meta: { total: 2, page: 1, limit: 20 },
    })
    await renderAndWaitForEvent('테스트 이벤트 1')
    const cards = screen.getAllByTestId('event-card-external')
    expect(cards).toHaveLength(2)
    cards.forEach(card => {
      expect(card.tagName).toBe('A')
      expect(card).toHaveAttribute('target', '_blank')
      expect(card).toHaveAttribute('rel', 'noopener noreferrer')
    })
    expect(cards[0]).toHaveAttribute('href', 'https://event-us.kr/event/1?ref=nexus.bccard.ai')
    expect(cards[1]).toHaveAttribute('href', 'https://event-us.kr/event/2?ref=nexus.bccard.ai')
  })

  it('linkUrl carries ref=nexus.bccard.ai', async () => {
    fetchEvents.mockResolvedValue({
      data: [makeEvent(5)],
      meta: { total: 1, page: 1, limit: 20 },
    })
    wrap(<Meet />)
    await waitFor(() => {
      expect(screen.getByText('테스트 이벤트 5')).toBeInTheDocument()
    })
    const card = screen.getByTestId('event-card-external')
    expect(card.getAttribute('href')).toContain('ref=nexus.bccard.ai')
  })

  it('shows empty state when API returns no events', async () => {
    fetchEvents.mockResolvedValue({
      data: [],
      meta: { total: 0, page: 1, limit: 20 },
    })
    wrap(<Meet />)
    await waitFor(() => {
      expect(screen.getByText('등록된 이벤트가 없어요.')).toBeInTheDocument()
    })
  })

  it('shows error state and retry button on API failure', async () => {
    fetchEvents.mockRejectedValue(new Error('서버 오류'))
    wrap(<Meet />)
    await waitFor(() => {
      expect(screen.getByText('다시 시도')).toBeInTheDocument()
    })
  })

  it('shows loading skeletons initially', () => {
    fetchEvents.mockReturnValue(new Promise(() => {}))
    wrap(<Meet />)
    const skeletons = document.querySelectorAll('.sk')
    expect(skeletons.length).toBeGreaterThan(0)
  })
})
