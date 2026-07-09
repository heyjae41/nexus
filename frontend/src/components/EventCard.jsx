import { useNavigate } from 'react-router-dom'
import { meetGrad, fmtKo } from '../utils/grads'
import { clickableProps } from '../utils/a11y'

/**
 * Shared EventCard — renders a meetup/event listing card.
 *
 * Static (internal) variant — default:
 *   compact=true  → Home page style (120px thumb, shorter meta)
 *   compact=false → Meet page style (140px thumb, full meta with host line)
 *   Navigates to /meet/:id on click.
 *
 * External variant (external=true):
 *   Renders as <a href={event.linkUrl} target="_blank">.
 *   Uses API card fields: coverImageUrl, eventStart (ISO), hostName,
 *   place, area, viewCount, priceText, category, eventSystemType, linkUrl.
 */

function fmtEventDate(iso) {
  const d = new Date(iso)
  const month = d.getMonth() + 1
  const day = d.getDate()
  const weekday = ['일', '월', '화', '수', '목', '금', '토'][d.getDay()]
  return `${month}월 ${day}일(${weekday})`
}

export default function EventCard({ event, index, compact = false, external = false }) {
  const navigate = useNavigate()
  const grad = meetGrad(index)

  if (external) {
    const thumbHeight = compact ? 120 : 140
    const dateLabel = event.eventStart ? fmtEventDate(event.eventStart) : ''
    const location = event.place || event.area || ''

    return (
      <a
        href={event.linkUrl}
        target="_blank"
        rel="noopener noreferrer"
        data-testid="event-card-external"
        style={{
          display: 'block',
          background: '#15151A',
          border: '1px solid rgba(255,255,255,.06)',
          borderRadius: 16,
          overflow: 'hidden',
          textDecoration: 'none',
          color: 'inherit',
        }}
      >
        <div style={{
          height: thumbHeight,
          position: 'relative',
          background: event.coverImageUrl
            ? `center/cover no-repeat url(${event.coverImageUrl}), ${grad}`
            : grad,
        }}>
          {event.category && (
            <span style={{
              position: 'absolute', top: 8, left: 10,
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: 10, fontWeight: 600, color: '#fff',
              background: 'rgba(0,0,0,.55)', padding: '3px 8px', borderRadius: 5,
            }}>
              {event.category}
            </span>
          )}
          {event.eventSystemType === 'online' && (
            <span style={{
              position: 'absolute', top: 8, right: 10,
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: 10, fontWeight: 600, color: '#fff',
              background: 'rgba(32,160,240,.85)', padding: '3px 8px', borderRadius: 5,
            }}>
              온라인
            </span>
          )}
          {dateLabel && (
            <span style={{
              position: 'absolute', bottom: 8, right: 10,
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: 10.5, fontWeight: 600, color: '#fff',
              background: 'rgba(0,0,0,.65)', padding: '3px 8px', borderRadius: 5,
            }}>
              {dateLabel}
            </span>
          )}
        </div>
        <div style={{ padding: compact ? '12px 14px 14px' : '14px 16px 16px' }}>
          <p style={{
            fontSize: compact ? 15 : 15.5, fontWeight: 700, color: '#ECECEF',
            lineHeight: 1.4, margin: '0 0 6px',
          }}>
            {event.title}
          </p>
          {!compact && event.hostName && (
            <p style={{ fontSize: 13, color: '#9a9aa4', margin: '0 0 6px' }}>{event.hostName}</p>
          )}
          <p style={{ fontSize: 12.5, color: '#7a7a84', margin: '0 0 4px' }}>
            📍{location} · 조회 {fmtKo(event.viewCount)}
          </p>
          {event.priceText && (
            <p style={{ fontSize: 12.5, color: '#9a9aa4', margin: 0 }}>{event.priceText}</p>
          )}
        </div>
      </a>
    )
  }

  // Internal (static data) variant
  const dateShort = event.date.replace('2026.', '').replace(/ \([^)]+\)/, '')
  const onClick = () => navigate(`/meet/${event.id}`)

  return (
    <div
      className="card"
      onClick={onClick}
      {...clickableProps(onClick, 'link')}
      style={{
        background: '#15151A',
        border: '1px solid rgba(255,255,255,.06)',
        borderRadius: 16, overflow: 'hidden',
      }}
    >
      <div style={{
        height: compact ? 120 : 140, position: 'relative',
        background: event.img
          ? `center/cover no-repeat url(${event.img}), ${grad}`
          : grad,
      }}>
        <span style={{
          position: 'absolute', top: 8, left: 10,
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: 10, fontWeight: 600, color: '#fff',
          background: 'rgba(0,0,0,.55)', padding: '3px 8px', borderRadius: 5,
        }}>
          {event.tag}
        </span>
        <span style={{
          position: 'absolute', bottom: 8, right: 10,
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: 10.5, fontWeight: 600, color: '#fff',
          background: 'rgba(0,0,0,.65)', padding: '3px 8px', borderRadius: 5,
        }}>
          {dateShort}
        </span>
      </div>
      <div style={{ padding: compact ? '12px 14px 14px' : '14px 16px 16px' }}>
        <p style={{
          fontSize: compact ? 15 : 15.5, fontWeight: 700, color: '#ECECEF',
          lineHeight: 1.4, margin: '0 0 6px',
        }}>
          {event.title}
        </p>
        {!compact && (
          <p style={{ fontSize: 13, color: '#9a9aa4', margin: '0 0 6px' }}>{event.host}</p>
        )}
        <p style={{ fontSize: 12.5, color: '#7a7a84', margin: 0 }}>
          📍{event.location} · {!compact && '👥'}{fmtKo(event.going)}명 참여{!compact && ' 예정'}
        </p>
      </div>
    </div>
  )
}
