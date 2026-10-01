import { describe, it, expect, vi } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useLatestFetch } from '../../frontend/src/hooks/useLatestFetch'
import { deferred } from './helpers'

const OPTS = { initial: null, fallbackError: '불러오지 못했습니다.' }

function abortError() {
  const err = new Error('aborted')
  err.name = 'AbortError'
  return err
}

describe('useLatestFetch', () => {
  it('늦게 도착한 이전 응답이 최신 응답을 덮어쓰지 않는다', async () => {
    const first = deferred()
    const second = deferred()
    const fetcher = vi.fn()
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise)
    const { result } = renderHook(() => useLatestFetch(fetcher, OPTS))

    act(() => { result.current.load() })
    await act(async () => { second.resolve('new') })
    await act(async () => { first.resolve('old') })

    expect(result.current.data).toBe('new')
    expect(result.current.loading).toBe(false)
  })

  it('새 요청 시 이전 요청의 signal 을 abort 한다', async () => {
    const fetcher = vi.fn(() => new Promise(() => {}))
    const { result } = renderHook(() => useLatestFetch(fetcher, OPTS))
    const firstSignal = fetcher.mock.calls[0][0].signal

    act(() => { result.current.load() })

    expect(firstSignal.aborted).toBe(true)
    expect(fetcher.mock.calls[1][0].signal.aborted).toBe(false)
  })

  it('AbortError 는 error 로 설정하지 않는다', async () => {
    const fetcher = vi.fn().mockRejectedValue(abortError())
    const { result } = renderHook(() => useLatestFetch(fetcher, OPTS))

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBe('')
  })

  it('err.message 가 비면 fallbackError 를 사용한다', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error(''))
    const { result } = renderHook(() => useLatestFetch(fetcher, OPTS))

    await waitFor(() => expect(result.current.error).toBe('불러오지 못했습니다.'))
  })

  it('err.message 가 있으면 그 메시지를 사용한다', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('API 오류'))
    const { result } = renderHook(() => useLatestFetch(fetcher, OPTS))

    await waitFor(() => expect(result.current.error).toBe('API 오류'))
  })

  it('onStart 는 매 로드마다 호출된다', async () => {
    const fetcher = vi.fn().mockResolvedValue('ok')
    const onStart = vi.fn()
    const { result } = renderHook(() => useLatestFetch(fetcher, { ...OPTS, onStart }))

    await waitFor(() => expect(result.current.loading).toBe(false))
    await act(async () => { await result.current.load() })

    expect(onStart).toHaveBeenCalledTimes(2)
    expect(fetcher).toHaveBeenCalledTimes(2)
  })

  it('reloadKey 가 바뀌면 다시 조회한다', async () => {
    const fetcher = vi.fn().mockResolvedValue('ok')
    const { rerender } = renderHook(
      ({ reloadKey }) => useLatestFetch(fetcher, { ...OPTS, reloadKey }),
      { initialProps: { reloadKey: 'a' } },
    )
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1))

    rerender({ reloadKey: 'b' })

    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2))
  })

  it('메모이즈되지 않은 inline onStart·fallbackError 로 재렌더해도 재조회하지 않는다', async () => {
    const fetcher = vi.fn().mockResolvedValue('ok')
    const { result, rerender } = renderHook(
      ({ tick }) => useLatestFetch(fetcher, {
        initial: null,
        fallbackError: `오류 ${tick}`,
        onStart: () => {},
      }),
      { initialProps: { tick: 0 } },
    )
    await waitFor(() => expect(result.current.loading).toBe(false))

    rerender({ tick: 1 })
    rerender({ tick: 2 })
    rerender({ tick: 3 })
    await act(async () => {})

    expect(fetcher).toHaveBeenCalledTimes(1)
  })

  it('최신 onStart 콜백을 사용한다', async () => {
    const fetcher = vi.fn().mockResolvedValue('ok')
    const before = vi.fn()
    const after = vi.fn()
    const { result, rerender } = renderHook(
      ({ onStart }) => useLatestFetch(fetcher, { ...OPTS, onStart }),
      { initialProps: { onStart: before } },
    )
    await waitFor(() => expect(result.current.loading).toBe(false))

    rerender({ onStart: after })
    await act(async () => { await result.current.load() })

    expect(after).toHaveBeenCalledTimes(1)
  })
})
