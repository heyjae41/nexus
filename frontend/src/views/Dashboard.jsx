import { useNavigate } from 'react-router-dom'
import { CLASSES } from '../data'
import { classGrad, articleGrad, fmtKo, initial } from '../utils/grads'

const CURATION_RECS = [
  { id: 'a1', title: 'GPT-5 시대, 금융권은 LLM을 어떻게 도입하고 있나', readTime: '7분' },
  { id: 'a2', title: '비전공 직장인이 6개월 만에 데이터 분석가로 이직한 법', readTime: '5분' },
  { id: 'a3', title: 'RAG vs 파인튜닝, 우리 회사엔 뭐가 맞을까', readTime: '8분' },
]

function StatCard({ num, label }) {
  return (
    <div style={{
      background: '#15151A', border: '1px solid rgba(255,255,255,.07)',
      borderRadius: 14, padding: '20px 18px',
    }}>
      <p style={{ fontSize: 28, fontWeight: 800, color: '#fff', margin: '0 0 6px' }}>{num}</p>
      <p style={{ fontSize: 13.5, color: '#9a9aa4', margin: 0 }}>{label}</p>
    </div>
  )
}

export default function Dashboard({ user, enrolled }) {
  const navigate = useNavigate()
  const userName = user || '김크레딧'

  const myClasses = (enrolled || [])
    .map(e => {
      const cls = CLASSES.find(c => c.id === e.id)
      return cls ? { ...cls, progress: e.progress } : null
    })
    .filter(Boolean)

  const hasClasses = myClasses.length > 0

  return (
    <main style={{ padding: '40px 40px 64px', maxWidth: 1080, margin: '0 auto' }}>
      {/* Profile header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 18, marginBottom: 36 }}>
        <div style={{
          width: 60, height: 60, borderRadius: '50%',
          background: 'linear-gradient(135deg,#E8123C,#7A0A22)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 22, fontWeight: 800, color: '#fff', flexShrink: 0,
        }}>
          {initial(userName)}
        </div>
        <div>
          <p style={{ fontSize: 22, fontWeight: 800, color: '#fff', margin: '0 0 4px' }}>
            {userName}님의 학습
          </p>
          <p style={{ fontSize: 14, color: '#9a9aa4', margin: 0 }}>이번 주도 한 스푼씩, 꾸준히 가봐요 🍯</p>
        </div>
      </div>

      {/* Stats */}
      <div className="rgrid-4" style={{ marginBottom: 40 }}>
        <StatCard num={myClasses.length} label="수강 중인 클래스" />
        <StatCard num="7일 🔥" label="연속 학습" />
        <StatCard num="12" label="작성한 커뮤니티 글" />
        <StatCard num="2" label="신청한 밋플" />
      </div>

      {/* Learning progress */}
      <section style={{ marginBottom: 40 }}>
        <h2 style={{ fontSize: 20, fontWeight: 800, color: '#fff', margin: '0 0 20px' }}>이어서 학습하기</h2>
        {hasClasses ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {myClasses.map((cls, i) => {
              const grad = classGrad(CLASSES.indexOf(cls))
              return (
                <div
                  key={cls.id}
                  style={{
                    background: '#15151A', border: '1px solid rgba(255,255,255,.07)',
                    borderRadius: 14, padding: '16px 18px',
                    display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap',
                  }}
                >
                  <div style={{ width: 90, height: 60, borderRadius: 8, background: grad, flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 200 }}>
                    <p style={{ fontSize: 15, fontWeight: 700, color: '#ECECEF', margin: '0 0 10px' }}>
                      {cls.title}
                    </p>
                    <div className="prog-track">
                      <div className="prog-fill" style={{ width: `${cls.progress}%` }} />
                    </div>
                    <p style={{ fontSize: 12, color: '#7a7a84', margin: '6px 0 0' }}>{cls.progress}% 완료</p>
                  </div>
                  <button
                    className="btn"
                    onClick={() => navigate(`/classes/${cls.id}`)}
                    style={{
                      background: '#E8123C', color: '#fff',
                      fontSize: 13.5, fontWeight: 700,
                      padding: '8px 18px', borderRadius: 10, flexShrink: 0,
                    }}
                  >
                    이어보기
                  </button>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="empty-state">
            <p style={{ fontSize: 24, marginBottom: 10 }}>📚</p>
            <p style={{ fontSize: 15, color: '#9a9aa4', marginBottom: 16 }}>아직 수강 중인 클래스가 없어요</p>
            <button
              className="btn"
              onClick={() => navigate('/classes')}
              style={{
                background: '#E8123C', color: '#fff',
                fontSize: 14, fontWeight: 700, padding: '10px 20px', borderRadius: 10,
              }}
            >
              클래스 둘러보기
            </button>
          </div>
        )}
      </section>

      {/* Recommended curation */}
      <section>
        <h2 style={{ fontSize: 20, fontWeight: 800, color: '#fff', margin: '0 0 20px' }}>추천 큐레이션</h2>
        <div className="rgrid-3">
          {CURATION_RECS.map((art, i) => (
            <div
              key={art.id}
              className="card"
              onClick={() => navigate(`/articles/${art.id}`)}
              style={{
                background: '#15151A', border: '1px solid rgba(255,255,255,.06)',
                borderRadius: 14, overflow: 'hidden',
              }}
            >
              <div style={{ height: 90, background: articleGrad(i) }} />
              <div style={{ padding: '12px 14px' }}>
                <p style={{
                  fontSize: 14, fontWeight: 700, color: '#ECECEF',
                  lineHeight: 1.4, margin: '0 0 6px',
                  display: '-webkit-box', WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical', overflow: 'hidden',
                }}>
                  {art.title}
                </p>
                <p style={{ fontSize: 12.5, color: '#7a7a84', margin: 0 }}>{art.readTime} 읽기</p>
              </div>
            </div>
          ))}
        </div>
      </section>
    </main>
  )
}
