import { useCallback, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { fetchHotpicks } from '../api/client'
import {
  FeedBadge, FeedCard, FeedChip, FeedChipGroup, FeedHeader, FeedPage, FeedState, FeedTag, FeedThumb,
  FeedTitle,
} from '../components/feedKit'
import { useLatestFetch } from '../hooks/useLatestFetch'
import { HD_CATS } from '../data'
import { fmtKo } from '../utils/grads'

const HOTDEAL_ORIGIN = 'https://open.paybooc.co.kr'
const PAGE_SIZE = 40

function imageUrl(deal) {
  const value = deal.content_image || deal.thumbnail
  if (!value) return null
  try {
    return new URL(value, HOTDEAL_ORIGIN).href
  } catch {
    return null
  }
}

function sourceUrl(deal) {
  try {
    const url = new URL(deal.source_url)
    return ['http:', 'https:'].includes(url.protocol) ? url.href : null
  } catch {
    return null
  }
}

function productName(deal) {
  return deal.product_name || deal.title || '상품명 미상'
}

function DealCard({ deal }) {
  const name = productName(deal)
  const image = imageUrl(deal)
  const href = sourceUrl(deal)
  const price = Number(deal.product_price) || 0
  const original = Number(deal.original_price) || 0
  const discount = Number(deal.discount_rate) || 0

  const body = (
    <>
      <FeedThumb
        image={image}
        alt={name}
        badge={discount > 0 && <FeedBadge color="#E8123C">-{discount}%</FeedBadge>}
      />

      <div style={{ padding: '12px 14px 14px' }}>
        <FeedTag>{deal.category || '기타'} · {deal.orgid || 'AI 핫픽'}</FeedTag>
        <FeedTitle>{name}</FeedTitle>
        {original > 0 && original !== price && (
          <p style={{ fontSize: 12, color: '#55555f', textDecoration: 'line-through', margin: '0 0 2px' }}>
            {fmtKo(original)}원
          </p>
        )}
        <p style={{ fontSize: 17, fontWeight: 800, color: '#fff', margin: 0 }}>
          {price > 0 ? `${fmtKo(price)}원` : '가격 정보 없음'}
        </p>
      </div>
    </>
  )

  return (
    <FeedCard href={href} ariaLabel={`${name} 상품 페이지 새 창에서 열기`} testId="hotdeal-card-link">
      {body}
    </FeedCard>
  )
}

const INITIAL_PAYLOAD = { posts: [], last_updated: null }

export default function Hotdeal() {
  const location = useLocation()
  const [cat, setCat] = useState('전체')
  const [page, setPage] = useState(1)
  const resetPage = useCallback(() => setPage(1), [])
  const { data: payload, loading, error, load } = useLatestFetch(fetchHotpicks, {
    initial: INITIAL_PAYLOAD,
    fallbackError: '핫딜을 불러오지 못했습니다.',
    reloadKey: location.key,
    onStart: resetPage,
  })
  const deals = payload.posts
  const categories = useMemo(() => {
    const present = new Set(deals.map(deal => deal.category || '기타'))
    const preferred = HD_CATS.slice(1).filter(category => present.has(category))
    const extras = [...present].filter(category => !preferred.includes(category)).sort()
    return ['전체', ...preferred, ...extras]
  }, [deals])
  const activeCat = categories.includes(cat) ? cat : '전체'
  const filtered = activeCat === '전체' ? deals : deals.filter(deal => deal.category === activeCat)
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const visibleDeals = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  return (
    <FeedPage footnote="데이터: open.paybooc.co.kr/bcai · BC카드 AI 핫픽 API">
      <FeedHeader
        eyebrow="AI HOTPICK · gemma 27B 추천"
        title="AI 추천 핫딜"
        summary={`매일 업데이트되는 AI 추천 특가 모음 · 총 ${filtered.length}개 — 수많은 상품 중 지금 가장 혜택 좋은 딜만 골라드립니다.`}
      >
        {payload.last_updated && (
          <p style={{ fontSize: 11.5, color: '#666672', margin: '7px 0 0' }}>
            API 최종 업데이트: {payload.last_updated}
          </p>
        )}
      </FeedHeader>

      <FeedChipGroup ariaLabel="핫딜 카테고리 필터">
        {categories.map(category => (
          <FeedChip key={category} active={activeCat === category} onClick={() => { setCat(category); setPage(1) }}>
            {category}
          </FeedChip>
        ))}
      </FeedChipGroup>

      <FeedState
        loading={loading}
        error={error}
        empty={filtered.length === 0}
        loadingText="최신 핫딜을 불러오는 중입니다."
        errorText="핫딜을 불러오지 못했습니다."
        emptyText="조건에 맞는 핫딜이 없습니다."
        onRetry={load}
      >
        <div className="rgrid-4">
          {visibleDeals.map(deal => (
            <DealCard key={`${deal.orgid || 'hotpick'}:${deal.article_id}`} deal={deal} />
          ))}
        </div>
        {totalPages > 1 && (
          <nav aria-label="핫딜 페이지" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, marginTop: 32 }}>
            <button
              className="btn"
              aria-label="이전 페이지"
              disabled={currentPage === 1}
              onClick={() => setPage(value => Math.max(1, value - 1))}
            >
              이전
            </button>
            <span role="status" aria-live="polite" style={{ color: '#9a9aa4', fontSize: 13 }}>
              {currentPage} / {totalPages}
            </span>
            <button
              className="btn"
              aria-label="다음 페이지"
              disabled={currentPage === totalPages}
              onClick={() => setPage(value => Math.min(totalPages, value + 1))}
            >
              다음
            </button>
          </nav>
        )}
      </FeedState>
    </FeedPage>
  )
}
