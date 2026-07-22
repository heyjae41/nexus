import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom'
import Hotdeal from '@/views/Hotdeal'

vi.mock('@/api/client', () => ({
  fetchHotpicks: vi.fn(),
}))

import { fetchHotpicks } from '@/api/client'

const payload = {
  title: 'AI 추천 핫딜 정보',
  last_updated: '2026-07-16 13:21:18',
  total_count: 2,
  posts: [
    {
      article_id: 1001,
      product_name: '최신 AI 핫딜 상품',
      title: '[상점] 최신 AI 핫딜 상품',
      source_url: 'https://shop.example/products/1001?from=hotpick',
      url: 'https://community.example/posts/1001',
      content_image: 'https://cdn.example/1001.jpg',
      category: '가전/디지털',
      orgid: 'fmkorea',
      product_price: 29900,
      original_price: 49900,
      discount_rate: 40,
    },
    {
      article_id: 1002,
      product_name: '인테리어 신상품',
      title: '[상점] 인테리어 신상품',
      source_url: 'https://shop.example/products/1002',
      thumbnail: 'https://cdn.example/1002.jpg',
      category: '홈/인테리어',
      orgid: 'ppomppu',
      product_price: 19800,
      original_price: null,
      discount_rate: null,
    },
  ],
}

function renderHotdeal({ withSameRouteLink = false } = {}) {
  return render(
    <MemoryRouter initialEntries={['/hotdeal']}>
      {withSameRouteLink && <Link to="/hotdeal">AI핫딜 다시 열기</Link>}
      <Routes>
        <Route path="/hotdeal" element={<Hotdeal />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Hotdeal — 실시간 AI 핫픽 API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchHotpicks.mockResolvedValue(payload)
  })

  it('페이지 진입과 동일 AI핫딜 메뉴 재클릭마다 API를 호출한다', async () => {
    renderHotdeal({ withSameRouteLink: true })
    expect(await screen.findByText('최신 AI 핫딜 상품')).toBeInTheDocument()
    expect(fetchHotpicks).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('link', { name: 'AI핫딜 다시 열기' }))
    await waitFor(() => expect(fetchHotpicks).toHaveBeenCalledTimes(2))
  })

  it('상품 카드 클릭 링크로 API source_url을 그대로 사용한다', async () => {
    renderHotdeal()
    const link = await screen.findByRole('link', { name: /최신 AI 핫딜 상품/ })
    expect(link).toHaveAttribute('href', payload.posts[0].source_url)
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).not.toHaveAttribute('href', payload.posts[0].url)
  })

  it('API에 존재하는 카테고리로 필터링한다', async () => {
    renderHotdeal()
    await screen.findByText('최신 AI 핫딜 상품')
    fireEvent.click(screen.getByRole('button', { name: '홈/인테리어' }))
    expect(screen.getByText('인테리어 신상품')).toBeInTheDocument()
    expect(screen.queryByText('최신 AI 핫딜 상품')).not.toBeInTheDocument()
  })

  it('API 오류를 안내하고 다시 시도한다', async () => {
    fetchHotpicks
      .mockRejectedValueOnce(new Error('핫픽 API 오류'))
      .mockResolvedValueOnce(payload)
    renderHotdeal()
    expect(await screen.findByRole('alert')).toHaveTextContent('핫픽 API 오류')
    fireEvent.click(screen.getByRole('button', { name: '다시 시도' }))
    expect(await screen.findByText('최신 AI 핫딜 상품')).toBeInTheDocument()
    expect(fetchHotpicks).toHaveBeenCalledTimes(2)
  })

  it('40개씩 페이지네이션해 수백 개 카드를 한 번에 만들지 않는다', async () => {
    const posts = Array.from({ length: 41 }, (_, index) => ({
      ...payload.posts[0],
      article_id: 2000 + index,
      product_name: `페이지 상품 ${index + 1}`,
      source_url: `https://shop.example/products/${2000 + index}`,
    }))
    fetchHotpicks.mockResolvedValue({ ...payload, total_count: posts.length, posts })
    renderHotdeal()

    expect(await screen.findByText('페이지 상품 40')).toBeInTheDocument()
    expect(screen.queryByText('페이지 상품 41')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '다음 페이지' }))
    expect(screen.getByText('페이지 상품 41')).toBeInTheDocument()
    expect(screen.queryByText('페이지 상품 1')).not.toBeInTheDocument()
  })

  it('응답 순서가 뒤집혀도 마지막 메뉴 요청만 표시하고 이전 요청을 취소한다', async () => {
    let resolveFirst
    let resolveSecond
    fetchHotpicks
      .mockImplementationOnce(() => new Promise(resolve => { resolveFirst = resolve }))
      .mockImplementationOnce(() => new Promise(resolve => { resolveSecond = resolve }))
    renderHotdeal({ withSameRouteLink: true })
    await waitFor(() => expect(fetchHotpicks).toHaveBeenCalledTimes(1))
    const firstSignal = fetchHotpicks.mock.calls[0][0].signal

    fireEvent.click(screen.getByRole('link', { name: 'AI핫딜 다시 열기' }))
    await waitFor(() => expect(fetchHotpicks).toHaveBeenCalledTimes(2))
    expect(firstSignal.aborted).toBe(true)
    resolveSecond({ ...payload, posts: [{ ...payload.posts[0], product_name: '최신 요청 상품' }] })
    expect(await screen.findByText('최신 요청 상품')).toBeInTheDocument()
    resolveFirst({ ...payload, posts: [{ ...payload.posts[0], product_name: '오래된 요청 상품' }] })
    await waitFor(() => expect(screen.queryByText('오래된 요청 상품')).not.toBeInTheDocument())
  })

  it('빈 응답을 안내하고 비 HTTP(S) source_url은 링크로 만들지 않는다', async () => {
    fetchHotpicks.mockResolvedValueOnce({ ...payload, total_count: 0, posts: [] })
    const empty = renderHotdeal()
    expect(await screen.findByText('조건에 맞는 핫딜이 없습니다.')).toBeInTheDocument()
    empty.unmount()

    fetchHotpicks.mockResolvedValueOnce({
      ...payload,
      posts: [{ ...payload.posts[0], product_name: '안전하지 않은 링크', source_url: 'javascript:alert(1)' }],
    })
    renderHotdeal()
    expect(await screen.findByText('안전하지 않은 링크')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /안전하지 않은 링크/ })).not.toBeInTheDocument()
  })
})
