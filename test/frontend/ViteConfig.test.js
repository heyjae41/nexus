import { describe, expect, it, vi } from 'vitest'
import { malformedUriGuard } from '../../frontend/vite.malformed-uri-guard.js'

function guardMiddleware() {
  const guard = malformedUriGuard()
  const use = vi.fn()
  guard.configureServer({ middlewares: { use } })
  return use.mock.calls[0][0]
}

describe('Vite malformed URI guard', () => {
  it('불완전한 percent 인코딩을 Vite 내부 미들웨어 전에 400으로 종료한다', () => {
    const middleware = guardMiddleware()
    const response = { setHeader: vi.fn(), end: vi.fn() }
    const next = vi.fn()

    middleware({ url: '/%' }, response, next)

    expect(response.statusCode).toBe(400)
    expect(response.setHeader).toHaveBeenCalledWith('Content-Type', 'text/plain; charset=utf-8')
    expect(response.end).toHaveBeenCalledWith('Bad Request')
    expect(next).not.toHaveBeenCalled()
  })

  it('정상 URI는 기존 Vite 처리 과정으로 전달한다', () => {
    const middleware = guardMiddleware()
    const response = { setHeader: vi.fn(), end: vi.fn() }
    const next = vi.fn()

    middleware({ url: '/classes?category=AI%20TECH' }, response, next)

    expect(next).toHaveBeenCalledOnce()
    expect(response.end).not.toHaveBeenCalled()
  })
})
