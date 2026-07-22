import { useState, useEffect, useCallback, useRef } from 'react'
import ArticleCard from '../components/ArticleCard'
import { ArticleListSkeleton } from '../components/Skeleton'
import { fetchArticles } from '../api/client'

const PAGE_SIZE = 20
const FORMAT_FILTERS = [
  { value: null, label: '전체' },
  { value: 'newsletter', label: '뉴스레터' },
  { value: 'column', label: '컬럼' },
  { value: 'guide', label: '가이드' },
]

export default function Curation() {
  const [articles, setArticles] = useState([])
  const [meta, setMeta] = useState(null)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [articleType, setArticleType] = useState(null)
  const latestRequest = useRef(0)

  const load = useCallback(async (p = 1, type = articleType) => {
    const requestId = ++latestRequest.current
    setLoading(true)
    setError(null)
    try {
      const json = await fetchArticles({ category: 'curation', type, page: p, size: PAGE_SIZE })
      if (requestId !== latestRequest.current) return
      const items = json.data ?? json.articles ?? []
      const metaInfo = json.meta ?? null
      setArticles(items)
      setMeta(metaInfo)
      setPage(p)
    } catch (err) {
      if (requestId === latestRequest.current) setError(err.message)
    } finally {
      if (requestId === latestRequest.current) setLoading(false)
    }
  }, [articleType])

  useEffect(() => { load(1) }, [load])

  const totalPages = meta ? Math.ceil(meta.total / PAGE_SIZE) : 1

  return (
    <main style={{ padding: '40px 40px 64px', maxWidth: 1080, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <p style={{
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: 11, fontWeight: 600, letterSpacing: '.06em',
          color: '#E8123C', margin: '0 0 10px',
        }}>
          CURATION · 테크 &amp; 비즈니스 인사이트
        </p>
        <h1 style={{
          fontSize: 32, fontWeight: 800, color: '#fff',
          letterSpacing: '-.03em', margin: '0 0 10px',
        }}>
          나를 위한 큐레이션
        </h1>
        <p style={{ fontSize: 15, color: '#9a9aa4', margin: 0 }}>
          매일 업데이트되는 AI 테크 강좌와 금융·커리어 인사이트. 출근길에 한 편씩.
        </p>
      </div>

      <div
        aria-label="글 포맷 필터"
        style={{
          display: 'flex', gap: 8, flexWrap: 'wrap',
          margin: '-8px 0 28px',
        }}
      >
        {FORMAT_FILTERS.map(({ value, label }) => {
          const active = articleType === value
          return (
            <button
              key={label}
              type="button"
              className="btn chip"
              aria-pressed={active}
              onClick={() => setArticleType(value)}
              style={{
                padding: '8px 16px', borderRadius: 20,
                border: active ? '1px solid #E8123C' : '1px solid rgba(255,255,255,.08)',
                background: active ? '#E8123C' : '#15151A',
                color: active ? '#fff' : '#b4b4be',
                fontSize: 13, fontWeight: 700,
              }}
            >
              {label}
            </button>
          )
        })}
      </div>

      {/* Article list */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {Array.from({ length: 6 }, (_, i) => <ArticleListSkeleton key={i} />)}
        </div>
      ) : error ? (
        <div className="empty-state">
          <p style={{ marginBottom: 12 }}>콘텐츠를 불러오지 못했습니다.</p>
          <button
            className="btn"
            onClick={() => load(1)}
            style={{
              background: '#E8123C', color: '#fff',
              padding: '10px 20px', borderRadius: 10, fontSize: 14, fontWeight: 700,
            }}
          >
            다시 시도
          </button>
        </div>
      ) : articles.length === 0 ? (
        <div className="empty-state">
          <p>아직 글이 없어요.</p>
        </div>
      ) : (
        <>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {articles.map((a, i) => (
              <ArticleCard key={a.id} article={a} index={i} variant="list" />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 40 }}>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
                <button
                  key={p}
                  className="btn"
                  onClick={() => { load(p); window.scrollTo({ top: 0, behavior: 'smooth' }) }}
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
            </div>
          )}
        </>
      )}
    </main>
  )
}
