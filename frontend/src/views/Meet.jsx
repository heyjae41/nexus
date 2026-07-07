import { EVENTS } from '../data'
import EventCard from '../components/EventCard'
import PageLabel from '../components/PageLabel'

export default function Meet() {
  return (
    <main style={{ padding: '40px 40px 64px', maxWidth: 1080, margin: '0 auto' }}>
      <div style={{ marginBottom: 28 }}>
        <PageLabel>meet.pl · AI 이벤트 &amp; 밋업</PageLabel>
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
