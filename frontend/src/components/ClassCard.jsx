import { useNavigate } from 'react-router-dom'
import { classGrad, fmtKo } from '../utils/grads'
import { clickableProps } from '../utils/a11y'

/**
 * Shared ClassCard — renders a class listing card.
 * compact=true  → Home page style (120px thumb, simpler meta)
 * compact=false → Classes page style (148px thumb, full meta + original price)
 */
export default function ClassCard({ cls, index, compact = false }) {
  const navigate = useNavigate()
  const grad = classGrad(index)
  const price = cls.price >= 1000000
    ? Math.floor(cls.price / 10000) + '만원'
    : fmtKo(cls.price) + '원'
  const onClick = () => navigate(`/classes/${cls.id}`)

  return (
    <div
      className="card"
      onClick={onClick}
      {...clickableProps(onClick, 'link')}
      style={{
        background: '#15151A',
        border: '1px solid rgba(255,255,255,.06)',
        borderRadius: 16, overflow: 'hidden',
      }}
    >
      <div style={{ height: compact ? 120 : 148, background: grad, position: 'relative' }}>
        <span style={{
          position: 'absolute', top: 8, left: 10,
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: 10, fontWeight: 600, color: '#fff',
          background: compact ? 'rgba(0,0,0,.5)' : 'rgba(0,0,0,.55)',
          padding: compact ? '3px 7px' : '3px 8px', borderRadius: 5,
        }}>
          {cls.category}
        </span>
        {compact ? (
          cls.tag && (
            <span style={{
              position: 'absolute', top: 8, right: 10,
              fontSize: 10, fontWeight: 700, color: '#E8123C',
              background: 'rgba(232,18,60,.15)', padding: '3px 7px', borderRadius: 5,
            }}>
              {cls.tag}
            </span>
          )
        ) : (
          cls.level && (
            <span style={{
              position: 'absolute', top: 8, right: 10,
              fontSize: 10, fontWeight: 700, color: '#fff',
              background: 'rgba(0,0,0,.45)', padding: '3px 8px', borderRadius: 5,
            }}>
              {cls.level}
            </span>
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
          lineHeight: 1.4, margin: '0 0 8px',
          display: '-webkit-box', WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical', overflow: 'hidden',
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
    </div>
  )
}
