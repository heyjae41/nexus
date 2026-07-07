import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CLASSES, CLASS_CATS } from '../data'
import { classGrad, fmtKo } from '../utils/grads'

function ClassCard({ cls, index }) {
  const navigate = useNavigate()
  const grad = classGrad(index)
  const price = cls.price >= 1000000
    ? Math.floor(cls.price / 10000) + '만원'
    : fmtKo(cls.price) + '원'

  return (
    <div
      className="card"
      onClick={() => navigate(`/classes/${cls.id}`)}
      style={{
        background: '#15151A', border: '1px solid rgba(255,255,255,.06)',
        borderRadius: 16, overflow: 'hidden',
      }}
    >
      <div style={{ height: 148, background: grad, position: 'relative' }}>
        <span style={{
          position: 'absolute', top: 8, left: 10,
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: 10, fontWeight: 600, color: '#fff',
          background: 'rgba(0,0,0,.55)', padding: '3px 8px', borderRadius: 5,
        }}>
          {cls.category}
        </span>
        {cls.level && (
          <span style={{
            position: 'absolute', top: 8, right: 10,
            fontSize: 10, fontWeight: 700, color: '#fff',
            background: 'rgba(0,0,0,.45)', padding: '3px 8px', borderRadius: 5,
          }}>
            {cls.level}
          </span>
        )}
      </div>
      <div style={{ padding: '12px 14px 16px' }}>
        {/* Tag line */}
        <p style={{ height: 13, margin: '0 0 6px' }}>
          {cls.tag ? (
            <span style={{ fontSize: 10.5, fontWeight: 700, color: '#E8123C', letterSpacing: '.04em' }}>
              {cls.tag}
            </span>
          ) : null}
        </p>
        <p style={{
          fontSize: 15.5, fontWeight: 700, color: '#ECECEF',
          lineHeight: 1.4, margin: '0 0 8px',
          display: '-webkit-box', WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical', overflow: 'hidden',
        }}>
          {cls.title}
        </p>
        <p style={{ fontSize: 12.5, color: '#7a7a84', margin: '0 0 10px' }}>
          {cls.instructor} · {cls.chapters}개 챕터 · {cls.rating}★
        </p>
        <p style={{ fontSize: 18, fontWeight: 800, color: '#fff', margin: 0 }}>
          {price}
          {cls.original > 0 && (
            <span style={{ fontSize: 13, color: '#55555f', textDecoration: 'line-through', marginLeft: 8 }}>
              {fmtKo(cls.original)}원
            </span>
          )}
        </p>
      </div>
    </div>
  )
}

export default function Classes() {
  const [cat, setCat] = useState('전체')

  const filtered = cat === '전체' ? CLASSES : CLASSES.filter(c => c.category === cat)

  return (
    <main style={{ padding: '40px 40px 64px', maxWidth: 1180, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <p style={{
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: 11, fontWeight: 600, letterSpacing: '.06em',
          color: '#E8123C', margin: '0 0 10px',
        }}>
          CLASS · 데이터사이언스 / AI
        </p>
        <h1 style={{ fontSize: 32, fontWeight: 800, color: '#fff', letterSpacing: '-.03em', margin: '0 0 8px' }}>
          금융 AI 클래스
        </h1>
        <p style={{ fontSize: 15, color: '#9a9aa4', margin: 0 }}>
          BC카드 실데이터로 배우는 금융·AI 실무 클래스. 입문부터 고급까지.
        </p>
      </div>

      {/* Category chips */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
        {CLASS_CATS.map(c => (
          <button
            key={c}
            className={`cat-chip${cat === c ? ' active' : ''} btn`}
            onClick={() => setCat(c)}
          >
            {c}
          </button>
        ))}
      </div>

      <p style={{ fontSize: 13.5, color: '#9a9aa4', marginBottom: 20 }}>
        {cat} · 총 {filtered.length}개 클래스
      </p>

      {/* Grid */}
      <div className="rgrid-3">
        {filtered.map((cls, i) => (
          <ClassCard key={cls.id} cls={cls} index={i} />
        ))}
      </div>
    </main>
  )
}
