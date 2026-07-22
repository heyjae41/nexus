import { useState, useCallback } from 'react'
import EventCard from '../components/EventCard'
import PageLabel from '../components/PageLabel'
import FilterChips from '../components/FilterChips'
import Pagination from '../components/Pagination'
import { ErrorRetry, EmptyMessage } from '../components/ListFeedback'
import { usePagedList } from '../hooks/usePagedList'
import { fetchEvents } from '../api/client'

const PAGE_SIZE = 20
const EVENT_BADGES = [
  { label: '전체', value: null },
  { label: 'IT/프로그래밍', value: 'IT/프로그래밍' },
  { label: 'AI', value: 'AI' },
  { label: '경제/금융', value: '경제/금융' },
]

export default function Meet() {
  const [category, setCategory] = useState(null)

  const fetchPage = useCallback(
    (p, selectedCategory = null) => fetchEvents({ category: selectedCategory, page: p, size: PAGE_SIZE }),
    [],
  )

  const { items: events, page, loading, error, load, totalPages } = usePagedList(fetchPage, PAGE_SIZE)

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

      <FilterChips
        options={EVENT_BADGES}
        value={category}
        onChange={(value) => { setCategory(value); load(1, value) }}
        ariaLabel="이벤트 배지 필터"
      />

      {loading ? (
        <div className="rgrid-3">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="sk" style={{ height: 220, borderRadius: 16 }} />
          ))}
        </div>
      ) : error ? (
        <ErrorRetry message="이벤트를 불러오지 못했습니다." onRetry={() => load(1, category)} />
      ) : events.length === 0 ? (
        <EmptyMessage>등록된 이벤트가 없어요.</EmptyMessage>
      ) : (
        <>
          <div className="rgrid-3">
            {events.map((event, i) => (
              <EventCard key={event.id} event={event} index={i} external />
            ))}
          </div>

          <Pagination
            totalPages={totalPages}
            page={page}
            ariaLabel="이벤트 페이지"
            onPage={(p) => { load(p, category); window.scrollTo({ top: 0, behavior: 'smooth' }) }}
          />
        </>
      )}
    </main>
  )
}
