import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * 단건 조회 공통 상태 — 로딩/에러 + 이전 요청 abort + 최신 요청만 반영(경합 가드).
 * fetcher({ signal }) 는 결과를 resolve 해야 한다. fetcher 교체가 곧 재조회 트리거이므로
 * 반드시 안정적인 참조(모듈 함수)이거나 useCallback 으로 메모이즈해야 한다 —
 * inline 함수를 넘기면 매 렌더마다 abort+재조회가 반복된다.
 * reloadKey 가 바뀌어도(예: location.key) 재조회한다.
 * onStart(매 요청 시작 시 호출, 예: 페이지 리셋)와 fallbackError 는 ref 로 최신값만 읽으므로
 * inline 으로 넘겨도 재조회를 유발하지 않는다.
 */
export function useLatestFetch(fetcher, { initial, fallbackError, reloadKey, onStart }) {
  const requestRef = useRef(0)
  const controllerRef = useRef(null)
  const [data, setData] = useState(initial)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const onStartRef = useRef(onStart)
  const fallbackErrorRef = useRef(fallbackError)
  onStartRef.current = onStart
  fallbackErrorRef.current = fallbackError

  const load = useCallback(async () => {
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller
    const requestId = ++requestRef.current
    setLoading(true)
    setError('')
    onStartRef.current?.()
    try {
      const result = await fetcher({ signal: controller.signal })
      if (requestId === requestRef.current) setData(result)
    } catch (err) {
      if (err?.name !== 'AbortError' && requestId === requestRef.current) {
        setError(err?.message || fallbackErrorRef.current)
      }
    } finally {
      if (requestId === requestRef.current) setLoading(false)
    }
  }, [fetcher])

  useEffect(() => {
    load()
    return () => controllerRef.current?.abort()
  }, [load, reloadKey])

  return { data, loading, error, load }
}
