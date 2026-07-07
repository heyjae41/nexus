import { useNavigate } from 'react-router-dom'
import { EVENTS } from '../data'
import { meetGrad, fmtKo } from '../utils/grads'

function EventCard({ event, index }) {
  const navigate = useNavigate()
  const grad = meetGrad(index)
  const dateShort = event.date.replace('2026.', '').replace(/ \([^)]+\)/, '')

  return (
    <div
      className="card"
      onClick={() => navigate(`/meet/${event.id}`)}
      style={{
        background: '#15151A', border: '1px solid rgba(255,255,255,.06)',
        borderRadius: 16, overflow: 'hidden',
      }}
    >
      <div style={{
        height: 140, position: 'relative',
        background: event.img ? `center/cover no-repeat url(${event.img}), ${grad}` : grad,
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
      <div style={{ padding: '14px 16px 16px' }}>
        <p style={{ fontSize: 15.5, fontWeight: 700, color: '#ECECEF', lineHeight: 1.4, margin: '0 0 6px' }}>
          {event.title}
        </p>
        <p style={{ fontSize: 13, color: '#9a9aa4', margin: '0 0 6px' }}>{event.host}</p>
        <p style={{ fontSize: 12.5, color: '#7a7a84', margin: 0 }}>
          📍{event.location} · 👥{fmtKo(event.going)}명 참여 예정
        </p>
      </div>
    </div>
  )
}

export default function Meet() {
  return (
    <main style={{ padding: '40px 40px 64px', maxWidth: 1080, margin: '0 auto' }}>
      <div style={{ marginBottom: 28 }}>
        <p style={{
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: 11, fontWeight: 600, letterSpacing: '.06em',
          color: '#E8123C', margin: '0 0 10px',
        }}>
          meet.pl · AI 이벤트 &amp; 밋업
        </p>
        <h1 style={{ fontSize: 32, fontWeight: 800, color: '#fff', letterSpacing: '-.03em', margin: '0 0 8px' }}>
          가야할 밋플
        </h1>
        <p style={{ fontSize: 15, color: '#9a9aa4', margin: 0 }}>
          현직자·커뮤니티와 만나는 AI 이벤트 모음. 온라인·오프라인을 가리지 않습니다.
        </p>
      </div>

      <div className="rgrid-3">
        {EVENTS.map((event, i) => (
          <EventCard key={event.id} event={event} index={i} />
        ))}
      </div>
    </main>
  )
}
