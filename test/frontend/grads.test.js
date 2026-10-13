import { describe, expect, it } from 'vitest'
import { coverBg, safeCoverUrl } from '../../frontend/src/utils/grads'

// 보안 LOW: 수집 데이터의 커버 URL 이 CSS background 에 그대로 들어가면
// `x), url(https://tracker/...)` 로 추가 요청·카드 위장이 가능하다.
describe('coverBg / safeCoverUrl', () => {
  const grad = 'linear-gradient(135deg,#000,#111)'

  it('http(s) 와 같은 출처 경로만 허용하고 url() 안을 인용한다', () => {
    expect(coverBg('https://img.example/a.png', grad)).toBe(
      'center/cover no-repeat url("https://img.example/a.png"), linear-gradient(135deg,#000,#111)',
    )
    expect(safeCoverUrl('/api/media/thumbnails/x.png')).toBe('/api/media/thumbnails/x.png')
  })

  it('javascript:·data:·프로토콜 상대·CSS 주입 시도는 그라디언트만 남긴다', () => {
    for (const bad of ['javascript:alert(1)', 'data:image/png;base64,AAAA', '//evil/x.png', '/\t/evil/x.png', '/\n\\evil', '', null, undefined, 42]) {
      expect(coverBg(bad, grad)).toBe(grad)
    }
    const injected = coverBg('https://img.example/a.png"), url("https://tracker/p', grad)
    expect(injected).toContain('url("https://img.example/a.png%22),%20url(%22https://tracker/p")')
    expect(injected).not.toContain('"), url("')
  })
})
