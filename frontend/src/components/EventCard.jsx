import { useNavigate } from 'react-router-dom'
import { meetGrad, fmtKo, coverBg } from '../utils/grads'
import { ExternalCard, ClickableCard, ThumbBadge } from './cardKit'

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
  const thumbHeight = compact ? 120 : 140
  const contentPad = compact ? '12px 14px 14px' : '14px 16px 16px'

  if (external) {
    const dateLabel = event.eventStart ? fmtEventDate(event.eventStart) : ''
    const location = event.place || event.area || ''

    return (
      <ExternalCard href={event.linkUrl} testId="event-card-external">
        <div style={{ height: thumbHeight, position: 'relative', background: coverBg(event.coverImageUrl, grad) }}>
          {event.category && <ThumbBadge>{event.category}</ThumbBadge>}
          {event.eventSystemType === 'online' && (
            <ThumbBadge pos="tr" bg="rgba(32,160,240,.85)">온라인</ThumbBadge>
          )}
          {dateLabel && <ThumbBadge pos="br" bg="rgba(0,0,0,.65)" size={10.5}>{dateLabel}</ThumbBadge>}
        </div>
        <div style={{ padding: contentPad }}>
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
      </ExternalCard>
    )
  }

  // Internal (static data) variant
  const dateShort = event.date.replace('2026.', '').replace(/ \([^)]+\)/, '')
  const onClick = () => navigate(`/meet/${event.id}`)

  return (
    <ClickableCard onClick={onClick}>
      <div style={{ height: thumbHeight, position: 'relative', background: coverBg(event.img, grad) }}>
        <ThumbBadge>{event.tag}</ThumbBadge>
        <ThumbBadge pos="br" bg="rgba(0,0,0,.65)" size={10.5}>{dateShort}</ThumbBadge>
      </div>
      <div style={{ padding: contentPad }}>
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
    </ClickableCard>
  )
}
