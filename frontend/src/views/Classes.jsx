import { useState } from 'react'
import { CLASSES, CLASS_CATS } from '../data'
import ClassCard from '../components/ClassCard'
import PageLabel from '../components/PageLabel'

export default function Classes() {
  const [cat, setCat] = useState('전체')

  const filtered = cat === '전체' ? CLASSES : CLASSES.filter(c => c.category === cat)

  return (
    <main style={{ padding: '40px 40px 64px', maxWidth: 1180, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <PageLabel>CLASS · 데이터사이언스 / AI</PageLabel>
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
