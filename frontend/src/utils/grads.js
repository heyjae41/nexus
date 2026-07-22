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

/* 커버 이미지가 있으면 그라디언트 위에 겹치고, 없으면 그라디언트만 */
export function coverBg(url, grad) {
  return url ? `center/cover no-repeat url(${url}), ${grad}` : grad
}
