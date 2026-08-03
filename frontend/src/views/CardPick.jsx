import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { fetchCardBenefits } from '../api/client'

const COMPANIES = ['전체', '하나카드', '우리카드']

const COMPANY_COLORS = {
  하나카드: '#008485',
  우리카드: '#0067AC',
}

function BenefitCard({ benefit }) {
  const [imgError, setImgError] = useState(false)
  const image = benefit.image_url
  const companyColor = COMPANY_COLORS[benefit.card_company] || '#6E6FF5'

  useEffect(() => setImgError(false), [image])

  return (
    <a
      className="card"
      href={benefit.detail_url}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`${benefit.title} 이벤트 페이지 새 창에서 열기`}
      data-testid="cardpick-card-link"
      style={{
        display: 'block', background: '#12121C', color: 'inherit', textDecoration: 'none',
        border: '1px solid rgba(255,255,255,.07)', borderRadius: 16, overflow: 'hidden',
      }}
    >
      <div style={{ aspectRatio: '1.45/1', position: 'relative', background: '#1a1a26', overflow: 'hidden' }}>
        {!imgError && image ? (
          <img
            src={image}
            alt=""
            loading="lazy"
            referrerPolicy="no-referrer"
            onError={() => setImgError(true)}
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          />
        ) : null}
        <span style={{
          position: 'absolute', top: 8, left: 8,
          background: companyColor, color: '#fff',
          fontSize: 11, fontWeight: 700,
          padding: '3px 8px', borderRadius: 5,
        }}>
          {benefit.card_company}
        </span>
      </div>

      <div style={{ padding: '12px 14px 14px' }}>
        {benefit.benefit_tags?.length > 0 && (
          <p style={{
            fontFamily: '"JetBrains Mono", monospace',
            fontSize: 10.5, fontWeight: 600, letterSpacing: '.03em',
            color: '#6E6FF5', margin: '0 0 6px',
          }}>
            {benefit.benefit_tags.map(tag => `#${tag}`).join(' ')}
          </p>
        )}
        <p style={{
          fontSize: 13.5, fontWeight: 600, color: '#ECECEF',
          lineHeight: 1.45, margin: '0 0 8px',
          minHeight: 38,
          display: '-webkit-box', WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical', overflow: 'hidden',
        }}>
          {benefit.title}
        </p>
        <p style={{ fontSize: 12, color: '#9a9aa4', margin: '0 0 3px' }}>
          {benefit.event_period}
        </p>
        {benefit.target_cards && (
          <p style={{
            fontSize: 11.5, color: '#666672', margin: 0,
            display: '-webkit-box', WebkitLineClamp: 1,
            WebkitBoxOrient: 'vertical', overflow: 'hidden',
          }}>
            대상: {benefit.target_cards}
          </p>
        )}
      </div>
    </a>
  )
}

export default function CardPick() {
  const location = useLocation()
  const requestRef = useRef(0)
  const controllerRef = useRef(null)
  const [company, setCompany] = useState('전체')
  const [benefits, setBenefits] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller
    const requestId = ++requestRef.current
    setLoading(true)
    setError('')
    try {
      const result = await fetchCardBenefits({ signal: controller.signal })
      if (requestId === requestRef.current) setBenefits(result)
    } catch (err) {
      if (err?.name !== 'AbortError' && requestId === requestRef.current) {
        setError(err?.message || '카드 혜택을 불러오지 못했습니다.')
      }
    } finally {
      if (requestId === requestRef.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    return () => controllerRef.current?.abort()
  }, [load, location.key])

  const filtered = company === '전체'
    ? benefits
    : benefits.filter(benefit => benefit.card_company === company)

  return (
    <main style={{ background: '#0A0A12', minHeight: '100vh', padding: '40px 40px 64px' }}>
      <div style={{ maxWidth: 1180, margin: '0 auto' }}>
        <div style={{ marginBottom: 28 }}>
          <p style={{
            fontFamily: '"JetBrains Mono", monospace',
            fontSize: 11, fontWeight: 600, letterSpacing: '.06em',
            color: '#6E6FF5', margin: '0 0 10px',
          }}>
            CARD.PICK · 해외여행 카드혜택 수집
          </p>
          <h1 style={{ fontSize: 32, fontWeight: 800, color: '#fff', letterSpacing: '-.03em', margin: '0 0 8px' }}>
            Card.Pick
          </h1>
          <p role="status" aria-live="polite" style={{ fontSize: 15, color: '#9a9aa4', margin: 0 }}>
            카드사별 해외여행 이벤트 혜택 모음 · 총 {filtered.length}개 — 할인·캐시백·무료이용 혜택만 골라 담았습니다.
          </p>
        </div>

        <div role="group" aria-label="카드사 필터" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 28 }}>
          {COMPANIES.map(name => (
            <button
              key={name}
              className="btn"
              aria-pressed={company === name}
              onClick={() => setCompany(name)}
              style={{
                padding: '7px 14px', borderRadius: 20,
                fontSize: 13.5, fontWeight: 600,
                background: company === name ? '#3E3FD9' : '#15151A',
                color: company === name ? '#fff' : '#b4b4be',
                border: company === name ? '1px solid #3E3FD9' : '1px solid rgba(255,255,255,.08)',
                transition: 'all .15s',
              }}
            >
              {name}
            </button>
          ))}
        </div>

        {loading ? (
          <p role="status" aria-live="polite" style={{ color: '#9a9aa4' }}>카드 혜택을 불러오는 중입니다.</p>
        ) : error ? (
          <div role="alert" style={{ color: '#9a9aa4', fontSize: 14 }}>
            카드 혜택을 불러오지 못했습니다. — {error}{' '}
            <button className="btn" onClick={load}>다시 시도</button>
          </div>
        ) : filtered.length === 0 ? (
          <p role="status" style={{ color: '#9a9aa4' }}>진행 중인 혜택이 없습니다.</p>
        ) : (
          <div className="rgrid-4">
            {filtered.map(benefit => (
              <BenefitCard key={benefit.id ?? benefit.detail_url} benefit={benefit} />
            ))}
          </div>
        )}

        <p style={{
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: 11.5, color: '#55555f',
          textAlign: 'center', marginTop: 40,
        }}>
          데이터: 하나카드·우리카드 여행/해외 이벤트 — 상세 혜택은 카드사 페이지에서 확인하세요
        </p>
      </div>
    </main>
  )
}
