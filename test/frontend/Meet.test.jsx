/**
 * Tests for Meet view — events rendered from mocked /api/events
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Meet from '@/views/Meet'

vi.mock('@/api/client', () => ({
  fetchEvents: vi.fn(),
}))

import { fetchEvents } from '@/api/client'

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

describe('Meet view — events from API', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders event cards from mocked /api/events', async () => {
    fetchEvents.mockResolvedValue({
      data: [makeEvent(1), makeEvent(2), makeEvent(3)],
      meta: { total: 3, page: 1, limit: 20 },
    })
    wrap(<Meet />)
    await waitFor(() => {
      expect(screen.getByText('테스트 이벤트 1')).toBeInTheDocument()
    })
    expect(screen.getByText('테스트 이벤트 2')).toBeInTheDocument()
    expect(screen.getByText('테스트 이벤트 3')).toBeInTheDocument()
  })

  it('each card is an <a> with target="_blank" and the linkUrl', async () => {
    fetchEvents.mockResolvedValue({
      data: [makeEvent(1), makeEvent(2)],
      meta: { total: 2, page: 1, limit: 20 },
    })
    wrap(<Meet />)
    await waitFor(() => {
      expect(screen.getByText('테스트 이벤트 1')).toBeInTheDocument()
    })
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
