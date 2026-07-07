import { useParams, useNavigate } from 'react-router-dom'
import { CLASSES, getCurriculum } from '../data'
import { classGrad, fmtKo } from '../utils/grads'

export default function ClassDetail({ enrolled, onEnroll }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const cls = CLASSES.find(c => c.id === id)
  if (!cls) return <div style={{ padding: 40, color: '#9a9aa4' }}>클래스를 찾을 수 없습니다.</div>

  const grad = classGrad(CLASSES.indexOf(cls))
  const curriculum = getCurriculum(cls)
  const isEnrolled = enrolled?.some(e => e.id === id)

  const price = cls.price >= 1000000
    ? Math.floor(cls.price / 10000) + '만원'
    : fmtKo(cls.price) + '원'

  const handleEnroll = () => {
    if (!isEnrolled) onEnroll(id)
    navigate(`/checkout/${id}`)
  }

  return (
    <main>
      {/* Banner */}
      <div style={{ background: '#0E0E13', borderBottom: '1px solid rgba(255,255,255,.07)', padding: '16px 40px' }}>
        <div style={{ maxWidth: 1080, margin: '0 auto' }}>
          <button
            className="back-link btn"
            onClick={() => navigate('/classes')}
            style={{ background: 'none', color: '#8a8a94', fontSize: 13.5, cursor: 'pointer', padding: 0, border: 'none', display: 'flex', alignItems: 'center', gap: 6 }}
          >
            ← 클래스 목록
          </button>
        </div>
      </div>

      <div style={{ maxWidth: 1080, margin: '0 auto', padding: '32px 40px 64px' }}>
        <div className="detailgrid detailgrid-class">
          {/* Left */}
          <div>
            <p style={{
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: 11.5, fontWeight: 600, letterSpacing: '.06em',
              color: '#E8123C', margin: '0 0 12px',
            }}>
              {cls.category} · {cls.level}
            </p>
            <h1 style={{ fontSize: 30, fontWeight: 800, color: '#fff', lineHeight: 1.25, letterSpacing: '-.025em', margin: '0 0 14px' }}>
              {cls.title}
            </h1>
            <p style={{ fontSize: 15.5, color: '#b4b4be', lineHeight: 1.7, margin: '0 0 20px' }}>{cls.desc}</p>

            {/* Meta */}
            <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', marginBottom: 28, fontSize: 14, color: '#9a9aa4' }}>
              <span>👩‍🏫 {cls.instructor}</span>
              <span>📚 {cls.chapters}개 챕터</span>
              <span>⏱ {cls.hours}시간</span>
              <span>⭐ {cls.rating}</span>
              <span>👥 {fmtKo(cls.students)}명 수강</span>
            </div>

            {/* Intro video placeholder */}
            <div style={{
              height: 240, background: grad, borderRadius: 14,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 15, color: 'rgba(255,255,255,.6)', marginBottom: 32,
              border: '1px solid rgba(255,255,255,.08)',
            }}>
              [ 강의 인트로 영상 ]
            </div>

            {/* Curriculum */}
            <h2 style={{ fontSize: 20, fontWeight: 800, color: '#fff', margin: '0 0 16px' }}>커리큘럼</h2>
            <div style={{ border: '1px solid rgba(255,255,255,.08)', borderRadius: 14, overflow: 'hidden' }}>
              {curriculum.map((ch, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 16,
                  padding: '13px 18px',
                  borderBottom: i < curriculum.length - 1 ? '1px solid rgba(255,255,255,.06)' : 'none',
                  background: '#13131A',
                }}>
                  <span style={{
                    fontFamily: '"JetBrains Mono", monospace',
                    fontSize: 11, fontWeight: 600, color: '#E8123C',
                    minWidth: 28,
                  }}>
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <span style={{ fontSize: 15, fontWeight: 600, color: '#dcdce2', flex: 1 }}>{ch}</span>
                  <span style={{ color: '#3a3a42', fontSize: 13 }}>▶</span>
                </div>
              ))}
            </div>
          </div>

          {/* Right — sticky purchase box */}
          <div className="sticky-box">
            <div style={{
              background: '#15151A',
              border: '1px solid rgba(255,255,255,.10)',
              borderRadius: 18, padding: '24px',
            }}>
              {cls.original > 0 && (
                <p style={{ fontSize: 14, color: '#55555f', textDecoration: 'line-through', margin: '0 0 4px' }}>
                  {fmtKo(cls.original)}원
                </p>
              )}
              <p style={{ fontSize: 30, fontWeight: 800, color: '#fff', margin: '0 0 18px' }}>
                {price}
              </p>
              <button
                className="btn"
                onClick={handleEnroll}
                style={{
                  width: '100%', background: '#E8123C', color: '#fff',
                  fontSize: 15, fontWeight: 700, padding: '13px 0',
                  borderRadius: 12, marginBottom: 10,
                }}
              >
                {isEnrolled ? '이어서 학습' : '수강 신청하기'}
              </button>
              <button className="btn ghost" style={{
                width: '100%', background: 'transparent', color: '#dcdce2',
                fontSize: 14, fontWeight: 600, padding: '12px 0',
                borderRadius: 12, border: '1px solid rgba(255,255,255,.14)',
              }}>
                구독으로 전체 수강
              </button>
              <div style={{ marginTop: 20, display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  '평생 소장 · 무제한 반복 수강',
                  'BC카드 실데이터 실습 환경 제공',
                  '수료증 발급 · 커뮤니티 멤버십',
                  '비씨카드 결제 시 5% 청구할인',
                ].map(b => (
                  <p key={b} style={{ fontSize: 13.5, color: '#9a9aa4', margin: 0, display: 'flex', gap: 8 }}>
                    <span style={{ color: '#1F8A5B', fontWeight: 700 }}>✓</span>{b}
                  </p>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
