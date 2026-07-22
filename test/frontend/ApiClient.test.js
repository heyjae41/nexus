import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchArticles, fetchClasses, fetchEvents, fetchHotpicks, fetchPosts } from '@/api/client'

afterEach(() => vi.unstubAllGlobals())

function mockResponse(body = { success: true, data: [], meta: { total: 0 } }) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: vi.fn().mockResolvedValue(body),
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('fetchArticles query contract', () => {
  it('선택한 글 포맷을 type 쿼리로 전송한다', async () => {
    const fetchMock = mockResponse()

    await fetchArticles({ category: 'curation', type: 'column', page: 1, size: 20 })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const url = new URL(fetchMock.mock.calls[0][0], 'http://nexus.test')
    expect(url.pathname).toBe('/api/articles')
    expect(url.searchParams.get('category')).toBe('curation')
    expect(url.searchParams.get('type')).toBe('column')
  })

  it('전체 필터에서는 type 쿼리를 생략한다', async () => {
    const fetchMock = mockResponse()

    await fetchArticles({ category: 'curation', type: null, page: 1, size: 20 })

    const url = new URL(fetchMock.mock.calls[0][0], 'http://nexus.test')
    expect(url.searchParams.has('type')).toBe(false)
  })
})

describe('fetchPosts query contract', () => {
  it('선택한 커뮤니티 배지를 tag 쿼리로 전송한다', async () => {
    const fetchMock = mockResponse()

    await fetchPosts({ tag: '기술자료', page: 1, size: 20 })

    const url = new URL(fetchMock.mock.calls[0][0], 'http://nexus.test')
    expect(url.pathname).toBe('/api/community/posts')
    expect(url.searchParams.get('tag')).toBe('기술자료')
  })
})

describe('fetchClasses query contract', () => {
  it('선택한 패스트캠퍼스 카테고리를 category 쿼리로 전송한다', async () => {
    const fetchMock = mockResponse()
    await fetchClasses({ category: 'AICREATIVE', page: 2, size: 20 })
    const url = new URL(fetchMock.mock.calls[0][0], 'http://nexus.test')
    expect(url.pathname).toBe('/api/classes')
    expect(url.searchParams.get('category')).toBe('AICREATIVE')
    expect(url.searchParams.get('page')).toBe('2')
  })

  it('전체 클래스에서는 category 쿼리를 생략한다', async () => {
    const fetchMock = mockResponse()
    await fetchClasses({ category: null, page: 1, size: 20 })
    const url = new URL(fetchMock.mock.calls[0][0], 'http://nexus.test')
    expect(url.searchParams.has('category')).toBe(false)
  })
})

describe('fetchEvents query contract', () => {
  it('선택한 이벤트 배지를 category 쿼리로 전송한다', async () => {
    const fetchMock = mockResponse()

    await fetchEvents({ category: 'IT/프로그래밍', page: 1, size: 20 })

    const url = new URL(fetchMock.mock.calls[0][0], 'http://nexus.test')
    expect(url.pathname).toBe('/api/events')
    expect(url.searchParams.get('category')).toBe('IT/프로그래밍')
  })

  it('전체 이벤트에서는 category 쿼리를 생략한다', async () => {
    const fetchMock = mockResponse()

    await fetchEvents({ category: null, page: 1, size: 20 })

    const url = new URL(fetchMock.mock.calls[0][0], 'http://nexus.test')
    expect(url.searchParams.has('category')).toBe(false)
  })
})

describe('fetchHotpicks external API contract', () => {
  it('캐시를 사용하지 않고 paybooc 최신 핫픽 API를 직접 호출한다', async () => {
    const fetchMock = mockResponse({ posts: [] })
    const controller = new AbortController()

    await fetchHotpicks({ signal: controller.signal })

    expect(fetchMock).toHaveBeenCalledWith(
      'https://open.paybooc.co.kr/bcai/api/hotpick/hotpicks',
      { cache: 'no-store', signal: controller.signal },
    )
  })

  it('non-2xx와 posts가 없는 잘못된 응답을 거부한다', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce({ ok: false, status: 503 }))
    await expect(fetchHotpicks()).rejects.toThrow('핫픽 API 오류 503')

    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce({
      ok: true,
      json: vi.fn().mockResolvedValue({ total_count: 1 }),
    }))
    await expect(fetchHotpicks()).rejects.toThrow('응답 형식이 올바르지 않습니다')
  })
})
