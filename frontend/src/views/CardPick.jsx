import { useCallback, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { fetchCardBenefits } from '../api/client'
import {
  FeedBadge, FeedCard, FeedChip, FeedChipGroup, FeedHeader, FeedPage, FeedState, FeedTag, FeedThumb,
  FeedTitle,
} from '../components/feedKit'
import { useLatestFetch } from '../hooks/useLatestFetch'

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
  const companyColor = COMPANY_COLORS[benefit.card_company] || '#6E6FF5'

  return (
    <FeedCard
      href={benefit.detail_url}
      ariaLabel={`${benefit.title} 이벤트 페이지 새 창에서 열기`}
      testId="cardpick-card-link"
    >
      <FeedThumb
        image={benefit.image_url}
        alt=""
        badge={<FeedBadge color={companyColor}>{benefit.card_company}</FeedBadge>}
      />

      <div style={{ padding: '12px 14px 14px' }}>
        {benefit.benefit_tags?.length > 0 && (
          <FeedTag>{benefit.benefit_tags.map(tag => `#${tag}`).join(' ')}</FeedTag>
        )}
        <FeedTitle>{benefit.title}</FeedTitle>
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
    </FeedCard>
  )
}

function BenefitGrid({ items, style }) {
  return (
    <div className="rgrid-4" style={style}>
      {items.map(benefit => (
        <BenefitCard key={benefit.id ?? benefit.detail_url} benefit={benefit} />
      ))}
    </div>
  )
}

function BenefitSection({ heading, items, gridStyle }) {
  if (items.length === 0) return null
  return (
    <>
      <h2 style={sectionHeadStyle}>
        {heading}
        <span style={sectionCountStyle}>{items.length}</span>
      </h2>
      <BenefitGrid items={items} style={gridStyle} />
    </>
  )
}

const INITIAL_DATA = { items: [], countries: [] }

export default function CardPick() {
  const location = useLocation()
  const [company, setCompany] = useState('전체')
  const [country, setCountry] = useState('전체')

  // 국가 필터는 ISO 코드(VN 등)와 해외공통(ALL)으로 서버에서 처리한다.
  const fetcher = useCallback(
    ({ signal }) => fetchCardBenefits({ country: country === '전체' ? null : country, signal }),
    [country],
  )
  const { data, loading, error, load } = useLatestFetch(fetcher, {
    initial: INITIAL_DATA,
    fallbackError: '카드 혜택을 불러오지 못했습니다.',
    reloadKey: location.key,
  })
  const benefits = data.items
  const countryFacets = data.countries
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

  const countryFacet = countryFacets.find(f => f.code === activeCountry)

  return (
    <FeedPage footnote="데이터: 하나카드·우리카드 여행/해외 이벤트 — 상세 혜택은 카드사 페이지에서 확인하세요">
      <FeedHeader
        eyebrow="CARD.PICK · 해외여행 카드혜택 수집"
        title="card.Pick"
        summary={`카드사별 해외여행 이벤트 혜택 모음 · 총 ${filtered.length}개 — 할인·캐시백·무료이용 혜택만 골라 담았습니다.`}
      />

      <FeedChipGroup ariaLabel="국가 필터" marginBottom={10}>
        {['전체', ...countryFacets.map(f => f.code)].map(code => {
          const facet = countryFacets.find(f => f.code === code)
          const label = facet?.name || code
          return (
            <FeedChip key={code} active={country === code} activeColor="#E8123C" onClick={() => setCountry(code)}>
              {facet ? `${facet.flag} ${label}` : label}
              {facet && (
                <span style={{ marginLeft: 5, fontSize: 11.5, opacity: .65 }}>{facet.count}</span>
              )}
            </FeedChip>
          )
        })}
      </FeedChipGroup>

      <FeedChipGroup ariaLabel="카드사 필터">
        {companies.map(name => (
          <FeedChip key={name} active={activeCompany === name} onClick={() => setCompany(name)}>
            {name}
            <span style={{ marginLeft: 5, fontSize: 11.5, opacity: .65 }}>
              {name === '전체' ? benefits.length : (companyCounts[name] || 0)}
            </span>
          </FeedChip>
        ))}
      </FeedChipGroup>

      <FeedState
        loading={loading}
        error={error}
        empty={filtered.length === 0}
        loadingText="카드 혜택을 불러오는 중입니다."
        errorText="카드 혜택을 불러오지 못했습니다."
        emptyText="진행 중인 혜택이 없습니다."
        onRetry={load}
      >
        {specific.length > 0 || commons.length > 0 ? (
          <>
            {/* 국가 선택 시: 특화 혜택과 '어디서나 쓰는' 해외공통을 시각적으로 분리 —
                칩의 건수(특화)와 첫 섹션이 일치해 "필터가 안 걸린 것 같은" 착시를 없앤다 */}
            <BenefitSection
              heading={<>{countryFacet?.flag} {countryFacet?.name || activeCountry} 특화 혜택</>}
              items={specific}
              gridStyle={{ marginBottom: 30 }}
            />
            <BenefitSection heading="🌏 해외 어디서나 쓰는 혜택" items={commons} />
          </>
        ) : (
          <BenefitGrid items={filtered} />
        )}
      </FeedState>
    </FeedPage>
  )
}
