import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { fetchHotpicks } from '../api/client'
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
  const [imgError, setImgError] = useState(false)
  const name = productName(deal)
  const image = imageUrl(deal)
  const href = sourceUrl(deal)
  const price = Number(deal.product_price) || 0
  const original = Number(deal.original_price) || 0
  const discount = Number(deal.discount_rate) || 0

  useEffect(() => setImgError(false), [image])

  const body = (
    <>
      <div style={{ aspectRatio: '1.45/1', position: 'relative', background: '#1a1a26', overflow: 'hidden' }}>
        {!imgError && image ? (
          <img
            src={image}
            alt={name}
            loading="lazy"
            onError={() => setImgError(true)}
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          />
        ) : null}
        {discount > 0 && (
          <span style={{
            position: 'absolute', top: 8, left: 8,
            background: '#E8123C', color: '#fff',
            fontSize: 11, fontWeight: 700,
            padding: '3px 8px', borderRadius: 5,
          }}>
            -{discount}%
          </span>
        )}
      </div>

      <div style={{ padding: '12px 14px 14px' }}>
        <p style={{
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: 10.5, fontWeight: 600, letterSpacing: '.03em',
          color: '#6E6FF5', margin: '0 0 6px',
        }}>
          {deal.category || '기타'} · {deal.orgid || 'AI 핫픽'}
        </p>
        <p style={{
          fontSize: 13.5, fontWeight: 600, color: '#ECECEF',
          lineHeight: 1.45, margin: '0 0 8px',
          minHeight: 38,
          display: '-webkit-box', WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical', overflow: 'hidden',
        }}>
          {name}
        </p>
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

  const cardStyle = {
    display: 'block', background: '#12121C', color: 'inherit', textDecoration: 'none',
    border: '1px solid rgba(255,255,255,.07)', borderRadius: 16, overflow: 'hidden',
  }
  if (!href) return <div className="card" style={cardStyle}>{body}</div>
  return (
    <a
      className="card"
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`${name} 상품 페이지 새 창에서 열기`}
      data-testid="hotdeal-card-link"
      style={cardStyle}
    >
      {body}
    </a>
  )
}

export default function Hotdeal() {
  const location = useLocation()
  const requestRef = useRef(0)
  const controllerRef = useRef(null)
  const [cat, setCat] = useState('전체')
  const [page, setPage] = useState(1)
  const [payload, setPayload] = useState({ posts: [], last_updated: null })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller
    const requestId = ++requestRef.current
    setLoading(true)
    setError('')
    setPage(1)
    try {
      const result = await fetchHotpicks({ signal: controller.signal })
      if (requestId === requestRef.current) setPayload(result)
    } catch (err) {
      if (err?.name !== 'AbortError' && requestId === requestRef.current) {
        setError(err?.message || '핫딜을 불러오지 못했습니다.')
      }
    } finally {
      if (requestId === requestRef.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    return () => controllerRef.current?.abort()
  }, [load, location.key])

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
    <main style={{ background: '#0A0A12', minHeight: '100vh', padding: '40px 40px 64px' }}>
      <div style={{ maxWidth: 1180, margin: '0 auto' }}>
        <div style={{ marginBottom: 28 }}>
          <p style={{
            fontFamily: '"JetBrains Mono", monospace',
            fontSize: 11, fontWeight: 600, letterSpacing: '.06em',
            color: '#6E6FF5', margin: '0 0 10px',
          }}>
            AI HOTPICK · gemma 27B 추천
          </p>
          <h1 style={{ fontSize: 32, fontWeight: 800, color: '#fff', letterSpacing: '-.03em', margin: '0 0 8px' }}>
            AI 추천 핫딜
          </h1>
          <p role="status" aria-live="polite" style={{ fontSize: 15, color: '#9a9aa4', margin: 0 }}>
            매일 업데이트되는 AI 추천 특가 모음 · 총 {filtered.length}개 — 수많은 상품 중 지금 가장 혜택 좋은 딜만 골라드립니다.
          </p>
          {payload.last_updated && (
            <p style={{ fontSize: 11.5, color: '#666672', margin: '7px 0 0' }}>
              API 최종 업데이트: {payload.last_updated}
            </p>
          )}
        </div>

        <div role="group" aria-label="핫딜 카테고리 필터" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 28 }}>
          {categories.map(category => (
            <button
              key={category}
              className="btn"
              aria-pressed={activeCat === category}
              onClick={() => { setCat(category); setPage(1) }}
              style={{
                padding: '7px 14px', borderRadius: 20,
                fontSize: 13.5, fontWeight: 600,
                background: activeCat === category ? '#3E3FD9' : '#15151A',
                color: activeCat === category ? '#fff' : '#b4b4be',
                border: activeCat === category ? '1px solid #3E3FD9' : '1px solid rgba(255,255,255,.08)',
                transition: 'all .15s',
              }}
            >
              {category}
            </button>
          ))}
        </div>

        {loading ? (
          <p role="status" aria-live="polite" style={{ color: '#9a9aa4' }}>최신 핫딜을 불러오는 중입니다.</p>
        ) : error ? (
          <div role="alert" style={{ color: '#9a9aa4', fontSize: 14 }}>
            핫딜을 불러오지 못했습니다. — {error}{' '}
            <button className="btn" onClick={load}>다시 시도</button>
          </div>
        ) : filtered.length === 0 ? (
          <p role="status" style={{ color: '#9a9aa4' }}>조건에 맞는 핫딜이 없습니다.</p>
        ) : (
          <>
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
          </>
        )}

        <p style={{
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: 11.5, color: '#55555f',
          textAlign: 'center', marginTop: 40,
        }}>
          데이터: open.paybooc.co.kr/bcai · BC카드 AI 핫픽 API
        </p>
      </div>
    </main>
  )
}
