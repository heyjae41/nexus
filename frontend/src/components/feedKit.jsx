import { useEffect, useState } from 'react'

/* 외부 피드 뷰(card.Pick·AI 핫딜) 공통 프리미티브 — 페이지 셸·헤더·칩·카드 조각·상태 표시 */

const MONO = '"JetBrains Mono", monospace'

const cardStyle = {
  display: 'block', background: '#12121C', color: 'inherit', textDecoration: 'none',
  border: '1px solid rgba(255,255,255,.07)', borderRadius: 16, overflow: 'hidden',
}

/* 카드 셸 — href 가 있으면 새 탭 <a>, 없으면(안전하지 않은 링크) 비링크 <div> */
export function FeedCard({ href, ariaLabel, testId, children }) {
  if (!href) return <div className="card" style={cardStyle}>{children}</div>
  return (
    <a
      className="card"
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={ariaLabel}
      data-testid={testId}
      style={cardStyle}
    >
      {children}
    </a>
  )
}

/* 썸네일 — 이미지 로드 실패 시 배경만 남기고, 좌상단에 badge 를 겹친다 */
export function FeedThumb({ image, alt, badge }) {
  const [imgError, setImgError] = useState(false)

  useEffect(() => setImgError(false), [image])

  return (
    <div style={{ aspectRatio: '1.45/1', position: 'relative', background: '#1a1a26', overflow: 'hidden' }}>
      {!imgError && image ? (
        <img
          src={image}
          alt={alt}
          loading="lazy"
          referrerPolicy="no-referrer"
          onError={() => setImgError(true)}
          style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
        />
      ) : null}
      {badge}
    </div>
  )
}

export function FeedBadge({ color, children }) {
  return (
    <span style={{
      position: 'absolute', top: 8, left: 8,
      background: color, color: '#fff',
      fontSize: 11, fontWeight: 700,
      padding: '3px 8px', borderRadius: 5,
    }}>
      {children}
    </span>
  )
}

export function FeedTag({ children }) {
  return (
    <p style={{
      fontFamily: MONO,
      fontSize: 10.5, fontWeight: 600, letterSpacing: '.03em',
      color: '#6E6FF5', margin: '0 0 6px',
    }}>
      {children}
    </p>
  )
}

export function FeedTitle({ children }) {
  return (
    <p style={{
      fontSize: 13.5, fontWeight: 600, color: '#ECECEF',
      lineHeight: 1.45, margin: '0 0 8px',
      minHeight: 38,
      display: '-webkit-box', WebkitLineClamp: 2,
      WebkitBoxOrient: 'vertical', overflow: 'hidden',
    }}>
      {children}
    </p>
  )
}

/* 페이지 셸 — 배경·최대폭 컨테이너·하단 데이터 출처 표기 */
export function FeedPage({ footnote, children }) {
  return (
    <main style={{ background: '#0A0A12', minHeight: '100vh', padding: '40px 40px 64px' }}>
      <div style={{ maxWidth: 1180, margin: '0 auto' }}>
        {children}
        <p style={{
          fontFamily: MONO,
          fontSize: 11.5, color: '#55555f',
          textAlign: 'center', marginTop: 40,
        }}>
          {footnote}
        </p>
      </div>
    </main>
  )
}

/* 페이지 헤더 — 아이브로우·제목·요약(status), children 은 요약 아래에 이어 붙는다 */
export function FeedHeader({ eyebrow, title, summary, children }) {
  return (
    <div style={{ marginBottom: 28 }}>
      <p style={{
        fontFamily: MONO,
        fontSize: 11, fontWeight: 600, letterSpacing: '.06em',
        color: '#6E6FF5', margin: '0 0 10px',
      }}>
        {eyebrow}
      </p>
      <h1 style={{ fontSize: 32, fontWeight: 800, color: '#fff', letterSpacing: '-.03em', margin: '0 0 8px' }}>
        {title}
      </h1>
      <p role="status" aria-live="polite" style={{ fontSize: 15, color: '#9a9aa4', margin: 0 }}>
        {summary}
      </p>
      {children}
    </div>
  )
}

/* 필터 알약 버튼 — 활성 색상은 호출측 지정 */
export function FeedChip({ active, activeColor = '#3E3FD9', onClick, children }) {
  return (
    <button
      className="btn"
      aria-pressed={active}
      onClick={onClick}
      style={{
        padding: '7px 14px', borderRadius: 20,
        fontSize: 13.5, fontWeight: 600,
        background: active ? activeColor : '#15151A',
        color: active ? '#fff' : '#b4b4be',
        border: active ? `1px solid ${activeColor}` : '1px solid rgba(255,255,255,.08)',
        transition: 'all .15s',
      }}
    >
      {children}
    </button>
  )
}

export function FeedChipGroup({ ariaLabel, marginBottom = 28, children }) {
  return (
    <div role="group" aria-label={ariaLabel} style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom }}>
      {children}
    </div>
  )
}

/* 로딩 → 에러(다시 시도) → 빈 목록 → children 순으로 표시 */
export function FeedState({ loading, error, empty, loadingText, errorText, emptyText, onRetry, children }) {
  if (loading) return <p role="status" aria-live="polite" style={{ color: '#9a9aa4' }}>{loadingText}</p>
  if (error) {
    return (
      <div role="alert" style={{ color: '#9a9aa4', fontSize: 14 }}>
        {errorText} — {error}{' '}
        <button className="btn" onClick={onRetry}>다시 시도</button>
      </div>
    )
  }
  if (empty) return <p role="status" style={{ color: '#9a9aa4' }}>{emptyText}</p>
  return children
}
