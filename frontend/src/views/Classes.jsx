import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchClasses } from '../api/client'
import ClassCard from '../components/ClassCard'
import PageLabel from '../components/PageLabel'
import Skeleton from '../components/Skeleton'

const CATEGORIES = [
  { code: null, label: '전체' },
  { code: 'DATASCIENCEDL', label: 'AI TECH' },
  { code: 'AICREATIVE', label: 'AI CREATIVE' },
  { code: 'BIZ', label: 'AI/업무생산성' },
]
const PAGE_SIZE = 20

export default function Classes() {
  const [category, setCategory] = useState(null)
  const [page, setPage] = useState(1)
  const [items, setItems] = useState([])
  const [meta, setMeta] = useState({ total: 0, page: 1, limit: PAGE_SIZE })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const latestRequest = useRef(0)

  const load = useCallback(async (nextPage = page, nextCategory = category) => {
    const requestId = ++latestRequest.current
    setLoading(true)
    setError(null)
    try {
      const json = await fetchClasses({ category: nextCategory, page: nextPage, size: PAGE_SIZE })
      if (requestId !== latestRequest.current) return
      setItems(json.data ?? [])
      setMeta(json.meta ?? { total: 0, page: nextPage, limit: PAGE_SIZE })
      setPage(nextPage)
    } catch (err) {
      if (requestId !== latestRequest.current) return
      setError(err.message)
    } finally {
      if (requestId === latestRequest.current) setLoading(false)
    }
  }, [category, page])

  useEffect(() => { load(1, category) }, [category]) // eslint-disable-line react-hooks/exhaustive-deps

  const selectCategory = code => {
    setPage(1)
    setCategory(code)
  }
  const totalPages = Math.ceil(meta.total / PAGE_SIZE)
  const activeLabel = CATEGORIES.find(c => c.code === category)?.label || '전체'

  return (
    <main style={{ padding: '40px 40px 64px', maxWidth: 1180, margin: '0 auto' }}>
      <div style={{ marginBottom: 28 }}>
        <PageLabel>CLASS · FASTCAMPUS CURATION</PageLabel>
        <h1 style={{ fontSize: 32, fontWeight: 800, color: '#fff', letterSpacing: '-.03em', margin: '0 0 8px' }}>
          지금 주목받는 AI 클래스
        </h1>
        <p style={{ fontSize: 15, color: '#9a9aa4', margin: 0 }}>
          패스트캠퍼스의 얼리버드·인기 급상승·BEST·NEW 과정만 모았습니다.
        </p>
      </div>

      <div role="group" aria-label="클래스 카테고리 필터" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
        {CATEGORIES.map(item => (
          <button
            key={item.label}
            className={`cat-chip${category === item.code ? ' active' : ''} btn`}
            aria-pressed={category === item.code}
            onClick={() => selectCategory(item.code)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <p role="status" aria-live="polite" style={{ fontSize: 13.5, color: '#9a9aa4', marginBottom: 20 }}>
        {activeLabel} · 총 {meta.total}개 클래스
      </p>

      {loading ? (
        <div role="status" aria-live="polite" aria-label="클래스 불러오는 중" className="rgrid-3">
          <Skeleton count={6} variant="article-grid" />
        </div>
      ) : error ? (
        <div role="alert" style={{ color: '#9a9aa4', fontSize: 14 }}>
          클래스를 불러오지 못했습니다. — {error}{' '}
          <button className="btn" onClick={() => load(page, category)}>다시 시도</button>
        </div>
      ) : items.length === 0 ? (
        <p style={{ color: '#9a9aa4', fontSize: 14 }}>조건에 맞는 클래스가 없어요.</p>
      ) : (
        <>
          <div className="rgrid-3">
            {items.map((course, index) => <ClassCard key={course.id} cls={course} index={index} />)}
          </div>
          {totalPages > 1 && (
            <nav aria-label="클래스 페이지" style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 28 }}>
              {Array.from({ length: totalPages }, (_, index) => index + 1).map(number => (
                <button
                  key={number}
                  className={`cat-chip${number === page ? ' active' : ''} btn`}
                  aria-current={number === page ? 'page' : undefined}
                  onClick={() => { load(number, category); window.scrollTo(0, 0) }}
                >
                  {number}
                </button>
              ))}
            </nav>
          )}
        </>
      )}
    </main>
  )
}
