import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

const INTERESTS = ['데이터 분석', 'LLM·생성형 AI', '금융 도메인', '생산성', '커리어', 'MLOps']

function ProgressBar({ step }) {
  const filled = { background: '#E8123C', borderRadius: 2 }
  const empty = { background: '#26262e', borderRadius: 2 }
  return (
    <div style={{ display: 'flex', gap: 6, marginBottom: 32 }}>
      {[1, 2, 3].map(s => (
        <div key={s} style={{ flex: 1, height: 4, ...(step >= s ? filled : empty) }} />
      ))}
    </div>
  )
}

export default function Onboarding({ onFinish }) {
  const navigate = useNavigate()
  const nameRef = useRef()
  const [step, setStep] = useState(1)
  const [role, setRole] = useState('직장인')
  const [interests, setInterests] = useState([])
  const [email, setEmail] = useState('')

  const obNext = () => setStep(s => Math.min(3, s + 1))
  const obPrev = () => setStep(s => Math.max(1, s - 1))

  const toggleInterest = (item) => {
    setInterests(prev =>
      prev.includes(item) ? prev.filter(i => i !== item) : [...prev, item]
    )
  }

  const finish = () => {
    const name = nameRef.current?.value?.trim() || '김크레딧'
    onFinish({ name, email: email.trim() || undefined, role, interests })
    setStep(1)
    navigate('/dashboard')
  }

  const cardStyle = (active) => ({
    border: `1px solid ${active ? '#E8123C' : 'rgba(255,255,255,.12)'}`,
    borderRadius: 14, padding: '16px 20px',
    cursor: 'pointer', background: active ? 'rgba(232,18,60,.06)' : '#15151A',
    transition: 'all .15s',
  })

  return (
    <main style={{ padding: '48px 40px 64px', maxWidth: 520, margin: '0 auto' }}>
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 32, justifyContent: 'center' }}>
        <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#E8123C' }} />
        <span style={{ fontSize: 20, fontWeight: 800, color: '#fff', letterSpacing: '-.03em' }}>NEXUS</span>
      </div>

      <ProgressBar step={step} />

      {/* Step 1 */}
      {step === 1 && (
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: '#fff', letterSpacing: '-.02em', margin: '0 0 8px' }}>
            반가워요 👋
          </h1>
          <p style={{ fontSize: 15, color: '#9a9aa4', margin: '0 0 28px' }}>3분이면 충분해요. 나에게 맞는 학습을 추천해드릴게요.</p>

          <label style={{ display: 'block', fontSize: 14, color: '#9a9aa4', marginBottom: 8 }}>이름</label>
          <input
            ref={nameRef}
            placeholder="예) 김크레딧"
            style={{
              width: '100%', background: '#15151A',
              border: '1px solid rgba(255,255,255,.12)', borderRadius: 10,
              padding: '12px 14px', fontSize: 15, color: '#ECECEF',
              fontFamily: 'inherit', outline: 'none', marginBottom: 16,
              boxSizing: 'border-box',
            }}
          />

          <label style={{ display: 'block', fontSize: 14, color: '#9a9aa4', marginBottom: 8 }}>이메일 (선택)</label>
          <input
            type="email"
            placeholder="이메일 (선택)"
            value={email}
            onChange={e => setEmail(e.target.value)}
            style={{
              width: '100%', background: '#15151A',
              border: '1px solid rgba(255,255,255,.12)', borderRadius: 10,
              padding: '12px 14px', fontSize: 15, color: '#ECECEF',
              fontFamily: 'inherit', outline: 'none', marginBottom: 24,
              boxSizing: 'border-box',
            }}
          />

          <p style={{ fontSize: 14, color: '#9a9aa4', marginBottom: 12 }}>저는...</p>
          <div
            role="radiogroup"
            style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 28 }}
          >
            {[['직장인', '💼'], ['개발자', '⌨️']].map(([r, icon]) => (
              <div
                key={r}
                role="radio"
                aria-checked={role === r}
                tabIndex={0}
                onClick={() => setRole(r)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setRole(r) } }}
                style={cardStyle(role === r)}
              >
                <p style={{ fontSize: 22, margin: '0 0 6px' }}>{icon}</p>
                <p style={{ fontSize: 15, fontWeight: 700, color: '#ECECEF', margin: 0 }}>{r}</p>
              </div>
            ))}
          </div>

          <button className="btn" onClick={obNext} style={{
            width: '100%', background: '#E8123C', color: '#fff',
            fontSize: 15, fontWeight: 700, padding: '13px 0', borderRadius: 12,
          }}>
            다음
          </button>
        </div>
      )}

      {/* Step 2 */}
      {step === 2 && (
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: '#fff', letterSpacing: '-.02em', margin: '0 0 8px' }}>
            관심 분야를 골라주세요
          </h1>
          <p style={{ fontSize: 15, color: '#9a9aa4', margin: '0 0 24px' }}>복수 선택 가능합니다.</p>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 32 }}>
            {INTERESTS.map(item => {
              const active = interests.includes(item)
              return (
                <button
                  key={item}
                  className="btn chip"
                  onClick={() => toggleInterest(item)}
                  aria-pressed={active}
                  style={{
                    padding: '8px 16px', borderRadius: 20, fontSize: 14, fontWeight: 600,
                    background: active ? '#E8123C' : '#15151A',
                    color: active ? '#fff' : '#b4b4be',
                    border: active ? '1px solid #E8123C' : '1px solid rgba(255,255,255,.12)',
                  }}
                >
                  {item}
                </button>
              )
            })}
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn ghost" onClick={obPrev} style={{
              flex: 1, background: 'transparent', color: '#dcdce2',
              fontSize: 14, fontWeight: 600, padding: '12px 0', borderRadius: 12,
              border: '1px solid rgba(255,255,255,.14)',
            }}>이전</button>
            <button className="btn" onClick={obNext} style={{
              flex: 2, background: '#E8123C', color: '#fff',
              fontSize: 15, fontWeight: 700, padding: '13px 0', borderRadius: 12,
            }}>다음</button>
          </div>
        </div>
      )}

      {/* Step 3 */}
      {step === 3 && (
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: '#fff', letterSpacing: '-.02em', margin: '0 0 24px' }}>
            준비 완료! 🎉
          </h1>

          <div style={{
            background: '#15151A', border: '1px solid rgba(255,255,255,.10)',
            borderRadius: 16, padding: '22px', marginBottom: 24,
          }}>
            <p style={{ fontSize: 14, color: '#55555f', textDecoration: 'line-through', margin: '0 0 4px' }}>29,000원</p>
            <p style={{ fontSize: 22, fontWeight: 800, color: '#fff', margin: '0 0 16px' }}>19,900원 / 월</p>
            {['120+ 클래스 무제한','현직자 커뮤니티 & 밋플 우선 신청','비씨카드 결제 시 첫 달 50% 할인'].map(b => (
              <p key={b} style={{ fontSize: 14, color: '#9a9aa4', margin: '0 0 8px', display: 'flex', gap: 8 }}>
                <span style={{ color: '#1F8A5B', fontWeight: 700 }}>✓</span>{b}
              </p>
            ))}
          </div>

          <button className="btn" onClick={finish} style={{
            width: '100%', background: '#E8123C', color: '#fff',
            fontSize: 15, fontWeight: 700, padding: '13px 0', borderRadius: 12, marginBottom: 12,
          }}>
            무료로 시작하기
          </button>
          <button onClick={finish} style={{
            width: '100%', background: 'none', border: 'none',
            fontSize: 14, color: '#7a7a84', cursor: 'pointer', padding: '10px 0',
          }}>
            나중에 할게요
          </button>
        </div>
      )}
    </main>
  )
}
