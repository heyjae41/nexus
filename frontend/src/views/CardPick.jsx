import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { fetchCardBenefits } from '../api/client'

// 필터 노출 순서 기준 — 데이터에 있는 카드사만 이 순서로 보여주고, 목록에 없던
// 신규 카드사는 뒤에 이어붙인다 (백엔드에 카드사가 추가돼도 프론트 수정 불필요)
const COMPANY_ORDER = ['BC카드', '하나카드', '우리카드', '현대카드', '삼성카드', '롯데카드', 'KB국민카드', '신한카드']

const sectionHeadStyle = {
  fontSize: 16, fontWeight: 700, color: '#ECECEF',
  letterSpacing: '-.01em', margin: '0 0 14px',
  display: 'flex', alignItems: 'center', gap: 8,
}
const sectionCountStyle = {
  fontFamily: '"JetBrains Mono", monospace',
  fontSize: 12, fontWeight: 600, color: '#6E6FF5',
}

const COMPANY_COLORS = {
  BC카드: '#E8123C',
  하나카드: '#008485',
  우리카드: '#0067AC',
  현대카드: '#111111',
  삼성카드: '#1428A0',
  롯데카드: '#DA291C',
  KB국민카드: '#FFB300',
  신한카드: '#0046FF',
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
        {benefit.benefit_summary && (
          <p style={{
            fontSize: 12, color: '#b4b4be',
            lineHeight: 1.5, margin: '0 0 8px',
            display: '-webkit-box', WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical', overflow: 'hidden',
          }}>
            {benefit.benefit_summary}
          </p>
        )}
        <p style={{ fontSize: 12, color: '#9a9aa4', margin: '0 0 3px' }}>
          {benefit.event_period}
          {benefit.countries?.length > 0 && (
            <span style={{ marginLeft: 8, color: '#666672', fontSize: 11.5 }}>
              {benefit.countries.slice(0, 2).join(' · ')}
            </span>
          )}
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
  const [country, setCountry] = useState('전체')
  const [benefits, setBenefits] = useState([])
  const [countryFacets, setCountryFacets] = useState([])
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
      // 국가 필터는 서버가 포함 관계(베트남 ⊃ 동남아 ⊃ 해외공통)로 전개·정렬한다
      const result = await fetchCardBenefits({
        country: country === '전체' ? null : country,
        signal: controller.signal,
      })
      if (requestId === requestRef.current) {
        setBenefits(result.items)
        setCountryFacets(result.countries)
      }
    } catch (err) {
      if (err?.name !== 'AbortError' && requestId === requestRef.current) {
        setError(err?.message || '카드 혜택을 불러오지 못했습니다.')
      }
    } finally {
      if (requestId === requestRef.current) setLoading(false)
    }
  }, [country])

  useEffect(() => {
    load()
    return () => controllerRef.current?.abort()
  }, [load, location.key])

  const present = new Set(benefits.map(benefit => benefit.card_company))
  const companies = [
    '전체',
    ...COMPANY_ORDER.filter(name => present.has(name)),
    ...[...present].filter(name => !COMPANY_ORDER.includes(name)).sort(),
  ]
  // 카드사 칩 개수 — 현재 국가 필터가 적용된 목록 기준 (국가 변경 시 자동 갱신)
  const companyCounts = benefits.reduce((acc, b) => {
    acc[b.card_company] = (acc[b.card_company] || 0) + 1
    return acc
  }, {})
  const activeCompany = companies.includes(company) ? company : '전체'
  const filtered = activeCompany === '전체'
    ? benefits
    : benefits.filter(benefit => benefit.card_company === activeCompany)
  // 국가 선택 시 서버가 내려주는 geo_match 로 섹션 분리 ('전체'면 둘 다 빈 배열)
  const activeCountry = country
  const specific = filtered.filter(b => b.geo_match && b.geo_match !== 'common')
  const commons = filtered.filter(b => b.geo_match === 'common')

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
            card.Pick
          </h1>
          <p role="status" aria-live="polite" style={{ fontSize: 15, color: '#9a9aa4', margin: 0 }}>
            카드사별 해외여행 이벤트 혜택 모음 · 총 {filtered.length}개 — 할인·캐시백·무료이용 혜택만 골라 담았습니다.
          </p>
        </div>

        <div role="group" aria-label="국가 필터" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
          {['전체', ...countryFacets.map(f => f.name)].map(name => {
            const facet = countryFacets.find(f => f.name === name)
            return (
              <button
                key={name}
                className="btn"
                aria-pressed={country === name}
                onClick={() => setCountry(name)}
                style={{
                  padding: '7px 14px', borderRadius: 20,
                  fontSize: 13.5, fontWeight: 600,
                  background: country === name ? '#E8123C' : '#15151A',
                  color: country === name ? '#fff' : '#b4b4be',
                  border: country === name ? '1px solid #E8123C' : '1px solid rgba(255,255,255,.08)',
                  transition: 'all .15s',
                }}
              >
                {facet ? `${facet.flag} ${facet.name}` : name}
                {facet && (
                  <span style={{ marginLeft: 5, fontSize: 11.5, opacity: .65 }}>{facet.count}</span>
                )}
              </button>
            )
          })}
        </div>

        <div role="group" aria-label="카드사 필터" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 28 }}>
          {companies.map(name => (
            <button
              key={name}
              className="btn"
              aria-pressed={activeCompany === name}
              onClick={() => setCompany(name)}
              style={{
                padding: '7px 14px', borderRadius: 20,
                fontSize: 13.5, fontWeight: 600,
                background: activeCompany === name ? '#3E3FD9' : '#15151A',
                color: activeCompany === name ? '#fff' : '#b4b4be',
                border: activeCompany === name ? '1px solid #3E3FD9' : '1px solid rgba(255,255,255,.08)',
                transition: 'all .15s',
              }}
            >
              {name}
              <span style={{ marginLeft: 5, fontSize: 11.5, opacity: .65 }}>
                {name === '전체' ? benefits.length : (companyCounts[name] || 0)}
              </span>
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
        ) : specific.length > 0 || commons.length > 0 ? (
          <>
            {/* 국가 선택 시: 특화 혜택과 '어디서나 쓰는' 해외공통을 시각적으로 분리 —
                칩의 건수(특화)와 첫 섹션이 일치해 "필터가 안 걸린 것 같은" 착시를 없앤다 */}
            {specific.length > 0 && (
              <>
                <h2 style={sectionHeadStyle}>
                  {countryFacets.find(f => f.name === activeCountry)?.flag} {activeCountry} 특화 혜택
                  <span style={sectionCountStyle}>{specific.length}</span>
                </h2>
                <div className="rgrid-4" style={{ marginBottom: 30 }}>
                  {specific.map(benefit => (
                    <BenefitCard key={benefit.id ?? benefit.detail_url} benefit={benefit} />
                  ))}
                </div>
              </>
            )}
            {commons.length > 0 && (
              <>
                <h2 style={sectionHeadStyle}>
                  🌏 해외 어디서나 쓰는 혜택
                  <span style={sectionCountStyle}>{commons.length}</span>
                </h2>
                <div className="rgrid-4">
                  {commons.map(benefit => (
                    <BenefitCard key={benefit.id ?? benefit.detail_url} benefit={benefit} />
                  ))}
                </div>
              </>
            )}
          </>
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
