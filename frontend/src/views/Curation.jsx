import { useState, useEffect, useCallback } from 'react'
import ArticleCard from '../components/ArticleCard'
import { ArticleListSkeleton } from '../components/Skeleton'
import { fetchArticles } from '../api/client'

const PAGE_SIZE = 20

export default function Curation() {
  const [articles, setArticles] = useState([])
  const [meta, setMeta] = useState(null)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async (p = 1) => {
    setLoading(true)
    setError(null)
    try {
      const json = await fetchArticles({ category: 'curation', page: p, size: PAGE_SIZE })
      const items = json.data ?? json.articles ?? []
      const metaInfo = json.meta ?? null
      setArticles(items)
      setMeta(metaInfo)
      setPage(p)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

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
