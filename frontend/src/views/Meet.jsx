import { useState, useEffect, useCallback, useRef } from 'react'
import EventCard from '../components/EventCard'
import PageLabel from '../components/PageLabel'
import { fetchEvents } from '../api/client'

const PAGE_SIZE = 20
const EVENT_BADGES = [
  { label: '전체', value: null },
  { label: 'IT/프로그래밍', value: 'IT/프로그래밍' },
  { label: 'AI', value: 'AI' },
  { label: '경제/금융', value: '경제/금융' },
]

export default function Meet() {
  const [events, setEvents] = useState([])
  const [meta, setMeta] = useState(null)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [category, setCategory] = useState(null)
  const latestRequest = useRef(0)

  const load = useCallback(async (p = 1, selectedCategory = null) => {
    const requestId = ++latestRequest.current
    setLoading(true)
    setError(null)
    try {
      const json = await fetchEvents({ category: selectedCategory, page: p, size: PAGE_SIZE })
      if (requestId !== latestRequest.current) return
      const items = json.data ?? []
      const metaInfo = json.meta ?? null
      setEvents(items)
      setMeta(metaInfo)
      setPage(p)
    } catch (err) {
      if (requestId === latestRequest.current) setError(err.message)
    } finally {
      if (requestId === latestRequest.current) setLoading(false)
    }
  }, [])

  useEffect(() => { load(1) }, [load])

  const totalPages = meta ? Math.ceil(meta.total / PAGE_SIZE) : 1

  return (
    <main style={{ padding: '40px 40px 64px', maxWidth: 1080, margin: '0 auto' }}>
      <div style={{ marginBottom: 18 }}>
        <PageLabel>meet.pl · AI 이벤트 &amp; 밋업</PageLabel>
        <h1 style={{ fontSize: 32, fontWeight: 800, color: '#fff', letterSpacing: '-.03em', margin: '0 0 8px' }}>
          가야할 밋플
        </h1>
        <p style={{ fontSize: 15, color: '#9a9aa4', margin: 0 }}>
          현직자·커뮤니티와 만나는 AI 이벤트 모음. 온라인·오프라인을 가리지 않습니다.
        </p>
      </div>

      <div
        role="group"
        aria-label="이벤트 배지 필터"
        style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 28 }}
      >
        {EVENT_BADGES.map(badge => {
          const active = category === badge.value
          return (
            <button
              key={badge.label}
              type="button"
              className="btn chip"
              aria-pressed={active}
              onClick={() => {
                setCategory(badge.value)
                load(1, badge.value)
              }}
              style={{
                padding: '7px 16px', borderRadius: 20, fontSize: 13.5, fontWeight: 600,
                background: active ? '#E8123C' : '#15151A',
                color: active ? '#fff' : '#b4b4be',
                border: active ? '1px solid #E8123C' : '1px solid rgba(255,255,255,.12)',
              }}
            >
              {badge.label}
            </button>
          )
        })}
      </div>

      {loading ? (
        <div className="rgrid-3">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="sk" style={{ height: 220, borderRadius: 16 }} />
          ))}
        </div>
      ) : error ? (
        <div className="empty-state">
          <p style={{ marginBottom: 12 }}>이벤트를 불러오지 못했습니다.</p>
          <button
            className="btn"
            onClick={() => load(1, category)}
            style={{
              background: '#E8123C', color: '#fff',
              padding: '10px 20px', borderRadius: 10, fontSize: 14, fontWeight: 700,
            }}
          >
            다시 시도
          </button>
        </div>
      ) : events.length === 0 ? (
        <div className="empty-state">
          <p>등록된 이벤트가 없어요.</p>
        </div>
      ) : (
        <>
          <div className="rgrid-3">
            {events.map((event, i) => (
              <EventCard key={event.id} event={event} index={i} external />
            ))}
          </div>

          {totalPages > 1 && (
            <nav
              aria-label="이벤트 페이지"
              style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 40 }}
            >
              {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
                <button
                  key={p}
                  className="btn"
                  aria-current={p === page ? 'page' : undefined}
                  onClick={() => { load(p, category); window.scrollTo({ top: 0, behavior: 'smooth' }) }}
                  style={{
                    width: 36, height: 36, borderRadius: 8,
                    fontSize: 14, fontWeight: 600,
                    background: p === page ? '#E8123C' : 'rgba(255,255,255,.06)',
                    color: p === page ? '#fff' : '#9a9aa4',
                    border: 'none',
                  }}
                >
                  {p}
                </button>
              ))}
            </nav>
          )}
        </>
      )}
    </main>
  )
}
