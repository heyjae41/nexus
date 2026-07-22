import { useState, useRef, useCallback, useEffect } from 'react'

/**
 * 목록 페이지 공통 상태 — 로딩/에러/메타/페이지 + 최신 요청만 반영(경합 가드).
 * fetchPage(page, ...args) 는 { data, meta } 형태를 resolve 해야 한다.
 * 마운트(및 fetchPage 교체) 시 1페이지를 자동 로드한다.
 */
export function usePagedList(fetchPage, pageSize = 20) {
  const [items, setItems] = useState([])
  const [meta, setMeta] = useState(null)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const latestRequest = useRef(0)

  const load = useCallback(async (p = 1, ...args) => {
    const requestId = ++latestRequest.current
    setLoading(true)
    setError(null)
    try {
      const json = await fetchPage(p, ...args)
      if (requestId !== latestRequest.current) return
      setItems(json.data ?? [])
      setMeta(json.meta ?? null)
      setPage(p)
    } catch (err) {
      if (requestId === latestRequest.current) setError(err.message)
    } finally {
      if (requestId === latestRequest.current) setLoading(false)
    }
  }, [fetchPage])

  useEffect(() => { load(1) }, [load])

  const totalPages = meta ? Math.ceil(meta.total / pageSize) : 1

  return { items, meta, page, loading, error, load, totalPages }
}
