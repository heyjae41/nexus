import { useNavigate } from 'react-router-dom'
import { meetGrad, fmtKo } from '../utils/grads'
import { clickableProps } from '../utils/a11y'

/**
 * Shared EventCard — renders a meetup/event listing card.
 * compact=true  → Home page style (120px thumb, shorter meta)
 * compact=false → Meet page style (140px thumb, full meta with host line)
 */
export default function EventCard({ event, index, compact = false }) {
  const navigate = useNavigate()
  const grad = meetGrad(index)
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
