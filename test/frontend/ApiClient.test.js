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

async function expectOmitsCategoryParam(fetchFn) {
  const fetchMock = mockResponse()
  await fetchFn({ category: null, page: 1, size: 20 })
  const url = new URL(fetchMock.mock.calls[0][0], 'http://nexus.test')
  expect(url.searchParams.has('category')).toBe(false)
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
    await expectOmitsCategoryParam(fetchClasses)
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
    await expectOmitsCategoryParam(fetchEvents)
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

function mockPartSequence(finalData) {
  // 조각 요청마다 {received} 를, 마지막 조각에는 finalData 를 돌려주는 fetch
  const fetchMock = vi.fn().mockImplementation(async (url, options) => {
    const payload = JSON.parse(options.body)
    const last = payload.index === payload.total - 1
    return {
      ok: true,
      json: async () => ({ success: true, data: last ? finalData : { received: payload.index } }),
    }
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('글 저장은 8KB 미만 조각으로 보낸다 (앞단 WAF 본문 제한)', () => {
  const mockSequence = mockPartSequence

  it('updateAuthoredArticle: 본문을 조각내 모두 8192바이트 미만 요청으로 보내고 마지막 응답을 돌려준다', async () => {
    const { updateAuthoredArticle } = await import('@/api/client')
    const fetchMock = mockSequence({ id: 7, title: '고친 제목' })
    const bodyHtml = '<p>' + '한글 본문 내용입니다. '.repeat(1500) + '</p>'
    expect(new TextEncoder().encode(bodyHtml).length).toBeGreaterThan(8192)

    const result = await updateAuthoredArticle('7', {
      articleType: 'guide', title: '고친 제목', summary: '요약', bodyHtml,
    })

    expect(result).toEqual({ id: 7, title: '고친 제목' })
    expect(fetchMock.mock.calls.length).toBeGreaterThan(1)
    const decoded = []
    for (const [url, options] of fetchMock.mock.calls) {
      expect(url).toBe('/api/admin/articles/parts')
      expect(options.method).toBe('POST')
      expect(new TextEncoder().encode(options.body).length).toBeLessThan(8192)
      const payload = JSON.parse(options.body)
      expect(payload).toMatchObject({ articleId: '7', articleType: 'guide', title: '고친 제목', summary: '요약' })
      decoded.push(payload)
    }
    const bytes = decoded
      .sort((a, b) => a.index - b.index)
      .flatMap(p => Array.from(Uint8Array.from(atob(p.data), c => c.charCodeAt(0))))
    expect(new TextDecoder().decode(Uint8Array.from(bytes))).toBe(bodyHtml)
  })

  it('createAuthoredArticle: 짧은 본문도 같은 경로로 1조각 전송하며 articleId 를 보내지 않는다', async () => {
    const { createAuthoredArticle } = await import('@/api/client')
    const fetchMock = mockSequence({ id: 9 })

    const result = await createAuthoredArticle({ articleType: 'column', title: '제목', summary: '', bodyHtml: '<p>짧다</p>' })

    expect(result).toEqual({ id: 9 })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const payload = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(payload.total).toBe(1)
    expect(payload).not.toHaveProperty('articleId')
  })

  it('제목·요약이 최대 길이의 한글이어도 모든 조각 요청이 8192바이트 미만이다', async () => {
    const { updateAuthoredArticle } = await import('@/api/client')
    const fetchMock = mockSequence({ id: 7 })
    const title = '가'.repeat(300)
    const summary = '나'.repeat(500)
    const bodyHtml = '<p>' + '다'.repeat(20000) + '</p>'

    await updateAuthoredArticle('7', { articleType: 'newsletter', title, summary, bodyHtml })

    for (const [, options] of fetchMock.mock.calls) {
      expect(new TextEncoder().encode(options.body).length).toBeLessThan(8192)
    }
  })

  it('마지막 조각 응답이 글이 아니면(조립 실패) 저장 성공으로 보지 않고 거부한다', async () => {
    const { createAuthoredArticle } = await import('@/api/client')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ success: true, data: { received: 0 } }),
    }))

    await expect(createAuthoredArticle({ articleType: 'column', title: '제목', summary: '', bodyHtml: '<p>짧다</p>' }))
      .rejects.toThrow('저장되지 않았습니다')
  })
})

describe('uploadArticleImage 조각 업로드', () => {
  // jsdom 의 File 에는 arrayBuffer 가 없다 — 브라우저와 같은 동작을 붙여 준다
  function makeFile(bytes, type) {
    const file = new File([bytes], 'x.png', { type })
    file.arrayBuffer = async () => bytes.buffer
    return file
  }

  it('모든 조각을 8192바이트 미만으로 보내고 진행률을 알리며 마지막 응답의 url 을 돌려준다', async () => {
    const { uploadArticleImage } = await import('@/api/client')
    const fetchMock = mockPartSequence({ url: '/api/media/authored/x.png' })
    const file = makeFile(new Uint8Array(12000), 'image/png')
    const progress = vi.fn()

    const result = await uploadArticleImage(file, progress)

    expect(result).toEqual({ url: '/api/media/authored/x.png' })
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(progress).toHaveBeenCalledTimes(3)
    for (const [url, options] of fetchMock.mock.calls) {
      expect(url).toBe('/api/admin/media/parts')
      expect(new TextEncoder().encode(options.body).length).toBeLessThan(8192)
      expect(JSON.parse(options.body).contentType).toBe('image/png')
    }
  })

  it('마지막 응답에 url 이 없으면 오류를 던진다', async () => {
    const { uploadArticleImage } = await import('@/api/client')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ success: true, data: { received: 0 } }) }))
    const file = makeFile(new Uint8Array(10), 'image/png')

    await expect(uploadArticleImage(file)).rejects.toThrow('이미지 주소를 받지 못했습니다.')
  })
})
