import { useNavigate } from 'react-router-dom'
import { classGrad, fmtKo, coverBg } from '../utils/grads'
import { ExternalCard, ClickableCard, ThumbBadge } from './cardKit'
import { clamp2 } from '../utils/cardStyles'

/**
 * Shared ClassCard — renders a class listing card.
 * compact=true  → Home page style (120px thumb, simpler meta)
 * compact=false → Classes page style (148px thumb, full meta + original price)
 */
export default function ClassCard({ cls, index, compact = false }) {
  const navigate = useNavigate()
  const grad = classGrad(index)

  if (cls.isExternal) {
    const isOpportunity = cls.sourceType === 'daker' || cls.sourceType === 'dacon'
    const hours = cls.runningTimeMinutes ? `${Math.floor(cls.runningTimeMinutes / 60)}시간` : null
    const price = Number.isFinite(cls.price) ? `${cls.price.toLocaleString('ko-KR')}원` : '가격 확인'
    const reward = Number.isFinite(cls.price) && cls.price > 0
      ? `총 상금 ${cls.price.toLocaleString('ko-KR')}원`
      : cls.qualification ? `혜택 ${cls.qualification}` : '상금·혜택 확인'
    return (
      <ExternalCard
        href={cls.linkUrl}
        ariaLabel={`${cls.title} (새 창에서 열림)`}
        testId="class-card-external"
      >
        <div style={{ height: 148, position: 'relative', background: coverBg(cls.coverImageUrl, grad) }}>
          <ThumbBadge>{cls.sourceCategoryName}</ThumbBadge>
          {cls.formatName && <ThumbBadge pos="tr" mono={false} weight={700}>{cls.formatName}</ThumbBadge>}
        </div>
        <div style={{ padding: '12px 14px 16px' }}>
          <div style={{ minHeight: 19, display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 6 }}>
            {(cls.badges || []).map(badge => (
              <span key={badge} style={{
                fontSize: 10.5, fontWeight: 700, color: '#E8123C', letterSpacing: '.03em',
              }}>{badge}</span>
            ))}
          </div>
          <p style={{
            fontSize: 15.5, fontWeight: 700, color: '#ECECEF', lineHeight: 1.4,
            margin: '0 0 8px', ...clamp2,
          }}>{cls.title}</p>
          {isOpportunity ? (
            <>
              {cls.summary && (
                <p style={{ fontSize: 12.5, color: '#9a9aa4', lineHeight: 1.45, margin: '0 0 6px', ...clamp2 }}>
                  {cls.summary}
                </p>
              )}
              {cls.category && (
                <p style={{ fontSize: 12, color: '#686872', margin: '0 0 8px' }}>{cls.category}</p>
              )}
              <p style={{ fontSize: 16, fontWeight: 800, color: '#fff', margin: 0 }}>{reward}</p>
            </>
          ) : (
            <>
              <p style={{ fontSize: 12.5, color: '#7a7a84', margin: '0 0 8px' }}>
                {[cls.category, cls.qualification, hours].filter(Boolean).join(' · ')}
              </p>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 7 }}>
                <p style={{ fontSize: 18, fontWeight: 800, color: '#fff', margin: 0 }}>{price}</p>
                {Number.isFinite(cls.original) && cls.original > cls.price && (
                  <span style={{ fontSize: 12, color: '#686872', textDecoration: 'line-through' }}>
                    {cls.original.toLocaleString('ko-KR')}원
                  </span>
                )}
              </div>
            </>
          )}
        </div>
      </ExternalCard>
    )
  }

  const price = cls.price >= 1000000
    ? Math.floor(cls.price / 10000) + '만원'
    : fmtKo(cls.price) + '원'
  const onClick = () => navigate(`/classes/${cls.id}`)

  return (
    <ClickableCard onClick={onClick}>
      <div style={{ height: compact ? 120 : 148, background: grad, position: 'relative' }}>
        <ThumbBadge>{cls.category}</ThumbBadge>
        {compact ? (
          cls.tag && (
            <ThumbBadge pos="tr" mono={false} weight={700} color="#E8123C" bg="rgba(232,18,60,.15)">
              {cls.tag}
            </ThumbBadge>
          )
        ) : (
          cls.level && (
            <ThumbBadge pos="tr" mono={false} weight={700} bg="rgba(0,0,0,.45)">
              {cls.level}
            </ThumbBadge>
          )
        )}
      </div>
      <div style={{ padding: compact ? '12px 14px 14px' : '12px 14px 16px' }}>
        <p style={{ height: 13, margin: compact ? '0 0 8px' : '0 0 6px' }}>
          {compact ? (
            <span style={{ fontSize: 12, color: '#E8123C', fontWeight: 600 }}>{cls.category}</span>
          ) : (
            cls.tag ? (
              <span style={{ fontSize: 10.5, fontWeight: 700, color: '#E8123C', letterSpacing: '.04em' }}>
                {cls.tag}
              </span>
            ) : null
          )}
        </p>
        <p style={{
          fontSize: compact ? 15 : 15.5, fontWeight: 700, color: '#ECECEF',
          lineHeight: 1.4, margin: '0 0 8px', ...clamp2,
        }}>
          {cls.title}
        </p>
        <p style={{ fontSize: 12.5, color: '#7a7a84', margin: '0 0 8px' }}>
          {compact
            ? `${cls.instructor} · ${cls.rating}★`
            : `${cls.instructor} · ${cls.chapters}개 챕터 · ${cls.rating}★`
          }
        </p>
        <p style={{ fontSize: compact ? 16 : 18, fontWeight: 800, color: '#fff', margin: 0 }}>
          {price}
          {!compact && cls.original > 0 && (
            <span style={{ fontSize: 13, color: '#55555f', textDecoration: 'line-through', marginLeft: 8 }}>
              {fmtKo(cls.original)}원
            </span>
          )}
        </p>
      </div>
    </ClickableCard>
  )
}
