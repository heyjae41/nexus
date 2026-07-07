import { useState } from 'react'
import { DEALS, HD_CATS } from '../data'
import { fmtKo } from '../utils/grads'

// Base URL for the paybooc hotdeal portal; per-item url field takes precedence when present
const HOTDEAL_BASE_URL = 'https://open.paybooc.co.kr'

function DealCard({ deal }) {
  const [imgError, setImgError] = useState(false)

  return (
    <div
      className="card"
      onClick={() => window.open(deal.url || HOTDEAL_BASE_URL, '_blank', 'noopener noreferrer')}
      style={{
        background: '#12121C', border: '1px solid rgba(255,255,255,.07)',
        borderRadius: 16, overflow: 'hidden',
      }}
    >
      {/* Image */}
      <div style={{ aspectRatio: '1.45/1', position: 'relative', background: '#1a1a26', overflow: 'hidden' }}>
        {!imgError && deal.img ? (
          <img
            src={deal.img}
            alt={deal.name}
            onError={() => setImgError(true)}
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          />
        ) : null}
        {deal.discount > 0 && (
          <span style={{
            position: 'absolute', top: 8, left: 8,
            background: '#E8123C', color: '#fff',
            fontSize: 11, fontWeight: 700,
            padding: '3px 8px', borderRadius: 5,
          }}>
            -{deal.discount}%
          </span>
        )}
      </div>

      <div style={{ padding: '12px 14px 14px' }}>
        <p style={{
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: 10.5, fontWeight: 600, letterSpacing: '.03em',
          color: '#6E6FF5', margin: '0 0 6px',
        }}>
          {deal.category} · {deal.channel}
        </p>
        <p style={{
          fontSize: 13.5, fontWeight: 600, color: '#ECECEF',
          lineHeight: 1.45, margin: '0 0 8px',
          minHeight: 38,
          display: '-webkit-box', WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical', overflow: 'hidden',
        }}>
          {deal.name}
        </p>
        {deal.original > 0 && (
          <p style={{ fontSize: 12, color: '#55555f', textDecoration: 'line-through', margin: '0 0 2px' }}>
            {fmtKo(deal.original)}원
          </p>
        )}
        <p style={{ fontSize: 17, fontWeight: 800, color: '#fff', margin: 0 }}>
          {fmtKo(deal.price)}원
        </p>
      </div>
    </div>
  )
}

export default function Hotdeal() {
  const [cat, setCat] = useState('전체')

  const filtered = cat === '전체' ? DEALS : DEALS.filter(d => d.category === cat)

  return (
    <main style={{ background: '#0A0A12', minHeight: '100vh', padding: '40px 40px 64px' }}>
      <div style={{ maxWidth: 1180, margin: '0 auto' }}>
        {/* Header */}
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
          <p style={{ fontSize: 15, color: '#9a9aa4', margin: 0 }}>
            매일 업데이트되는 AI 추천 특가 모음 · 총 {filtered.length}개 — 수많은 상품 중 지금 가장 혜택 좋은 딜만 골라드립니다.
          </p>
        </div>

        {/* Category chips */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 28 }}>
          {HD_CATS.map(c => (
            <button
              key={c}
              className="btn"
              onClick={() => setCat(c)}
              style={{
                padding: '7px 14px', borderRadius: 20,
                fontSize: 13.5, fontWeight: 600,
                background: cat === c ? '#3E3FD9' : '#15151A',
                color: cat === c ? '#fff' : '#b4b4be',
                border: cat === c ? '1px solid #3E3FD9' : '1px solid rgba(255,255,255,.08)',
                transition: 'all .15s',
              }}
            >
              {c}
            </button>
          ))}
        </div>

        {/* Grid */}
        <div className="rgrid-4">
          {filtered.map((deal, i) => (
            <DealCard key={i} deal={deal} />
          ))}
        </div>

        {/* Footer note */}
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
