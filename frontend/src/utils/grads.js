/* Gradient palette — §1.5 */
const GRADS = [
  'linear-gradient(135deg,#E8123C,#7A0A22)',   // 0 red
  'linear-gradient(135deg,#3E3FD9,#1A1A6E)',   // 1 blue
  'linear-gradient(135deg,#1F8A5B,#0C3D28)',   // 2 green
  'linear-gradient(135deg,#D98324,#5A360C)',   // 3 orange
  'linear-gradient(135deg,#8B2FC9,#3A0F58)',   // 4 purple
  'linear-gradient(135deg,#1593A6,#093E47)',   // 5 teal
  'linear-gradient(135deg,#C2185B,#5A0A2A)',   // 6 magenta
  'linear-gradient(135deg,#455A64,#1C2429)',   // 7 gray
]

function grads(i) {
  return GRADS[((i % 8) + 8) % 8]
}

export function classGrad(i) { return grads(i) }
export function articleGrad(i) { return grads(i + 2) }
export function communityAvatarGrad(i) { return grads(i + 1) }
export function meetGrad(i) { return grads(i + 3) }

export function fmtKo(n) { return (n || 0).toLocaleString('ko-KR') }
export function fmtEn(n) { return (n || 0).toLocaleString('en-US') }

export function fmtPrice(price) {
  if (price >= 1000000) {
    return Math.floor(price / 10000) + '만원'
  }
  return fmtKo(price) + '원'
}

export function initial(name) {
  return name ? name[0] : '?'
}

/* 수집 데이터의 커버 URL 은 http(s)·같은 출처 경로만 — 그 외는 그라디언트만 쓴다 */
export function safeCoverUrl(url) {
  if (typeof url !== 'string') return null
  const value = url.trim()
  if (/^\/(?![/\\])/.test(value)) return value
  try {
    const parsed = new URL(value)
    return ['http:', 'https:'].includes(parsed.protocol) ? parsed.href : null
  } catch {
    return null
  }
}

/* 커버 이미지가 있으면 그라디언트 위에 겹치고, 없으면 그라디언트만.
   url() 안은 JSON 문자열로 인용해 `x), url(https://tracker/...)` 식의 CSS 주입을 막는다 */
export function coverBg(url, grad) {
  const safe = safeCoverUrl(url)
  return safe ? `center/cover no-repeat url(${JSON.stringify(safe)}), ${grad}` : grad
}
