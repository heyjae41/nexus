import { useState, useCallback } from 'react'
import ArticleCard from '../components/ArticleCard'
import { ArticleListSkeleton } from '../components/Skeleton'
import PageLabel from '../components/PageLabel'
import FilterChips from '../components/FilterChips'
import Pagination from '../components/Pagination'
import { ErrorRetry, EmptyMessage } from '../components/ListFeedback'
import { usePagedList } from '../hooks/usePagedList'
import { fetchArticles } from '../api/client'

const PAGE_SIZE = 20
const FORMAT_FILTERS = [
  { value: null, label: '전체' },
  { value: 'newsletter', label: '뉴스레터' },
  { value: 'column', label: '컬럼' },
  { value: 'guide', label: '가이드' },
]

export default function Curation() {
  const [articleType, setArticleType] = useState(null)

  const fetchPage = useCallback(async (p, type = articleType) => {
    const json = await fetchArticles({ category: 'curation', type, page: p, size: PAGE_SIZE })
    return { data: json.data ?? json.articles ?? [], meta: json.meta ?? null }
  }, [articleType])

  const { items: articles, page, loading, error, load, totalPages } = usePagedList(fetchPage, PAGE_SIZE)

  return (
    <main style={{ padding: '40px 40px 64px', maxWidth: 1080, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <PageLabel>CURATION · 테크 &amp; 비즈니스 인사이트</PageLabel>
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

      <FilterChips
        options={FORMAT_FILTERS}
        value={articleType}
        onChange={setArticleType}
        ariaLabel="글 포맷 필터"
        style={{ margin: '-8px 0 28px' }}
      />

      {/* Article list */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {Array.from({ length: 6 }, (_, i) => <ArticleListSkeleton key={i} />)}
        </div>
      ) : error ? (
        <ErrorRetry message="콘텐츠를 불러오지 못했습니다." onRetry={() => load(1)} />
      ) : articles.length === 0 ? (
        <EmptyMessage>아직 글이 없어요.</EmptyMessage>
      ) : (
        <>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {articles.map((a, i) => (
              <ArticleCard key={a.id} article={a} index={i} variant="list" />
            ))}
          </div>

          <Pagination
            totalPages={totalPages}
            page={page}
            ariaLabel="글 페이지"
            onPage={(p) => { load(p); window.scrollTo({ top: 0, behavior: 'smooth' }) }}
          />
        </>
      )}
    </main>
  )
}
