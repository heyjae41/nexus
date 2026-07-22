import { clickableProps } from '../utils/a11y'

/* 카드 공통 프리미티브 — ArticleCard/ClassCard/EventCard 가 공유하는 셸·뱃지·썸네일 */

const shellStyle = {
  background: '#15151A',
  border: '1px solid rgba(255,255,255,.06)',
  borderRadius: 16,
  overflow: 'hidden',
}

/* 외부 수집 콘텐츠 카드 — 새 탭 <a> 셸 */
export function ExternalCard({ href, ariaLabel, testId, children }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={ariaLabel}
      data-testid={testId}
      style={{ display: 'block', textDecoration: 'none', color: 'inherit', ...shellStyle }}
    >
      {children}
    </a>
  )
}

/* 내부 이동 카드 — 클릭·키보드 접근 가능한 div 셸 */
export function ClickableCard({ onClick, children }) {
  return (
    <div className="card" onClick={onClick} {...clickableProps(onClick, 'link')} style={shellStyle}>
      {children}
    </div>
  )
}

/* 썸네일 위 오버레이 뱃지 (기본: JetBrains Mono 흰 글씨 + 반투명 검정) */
const BADGE_POS = {
  tl: { top: 8, left: 10 },
  tr: { top: 8, right: 10 },
  br: { bottom: 8, right: 10 },
}

export function ThumbBadge({
  pos = 'tl', bg = 'rgba(0,0,0,.55)', color = '#fff',
  size = 10, weight = 600, mono = true, children,
}) {
  return (
    <span style={{
      position: 'absolute', ...BADGE_POS[pos],
      ...(mono ? { fontFamily: '"JetBrains Mono", monospace' } : {}),
      fontSize: size, fontWeight: weight, color,
      background: bg, padding: '3px 8px', borderRadius: 5,
    }}>
      {children}
    </span>
  )
}

/* 그라디언트 배경 위 실사 썸네일 — 로드 실패 시 그라디언트가 남는다 */
export function ThumbImage({ src }) {
  if (!src) return null
  return (
    <img
      src={src}
      alt=""
      loading="lazy"
      onError={(e) => { e.currentTarget.style.display = 'none' }}
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }}
    />
  )
}
