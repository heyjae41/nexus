import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { checkNickname } from '../api/client'
import { INTEREST_OPTIONS, ROLE_OPTIONS } from '../data/authOptions'
import { passwordMissing } from '../utils/password'

const inputStyle = {
  width: '100%', boxSizing: 'border-box', background: '#15151A',
  border: '1px solid rgba(255,255,255,.12)', borderRadius: 10,
  padding: '12px 14px', fontSize: 15, color: '#ECECEF', fontFamily: 'inherit',
}

function ProgressBar({ step }) {
  return (
    <div aria-label={`회원가입 ${Math.min(step, 3)}단계`} style={{ display: 'flex', gap: 6, marginBottom: 32 }}>
      {[1, 2, 3].map(value => (
        <div key={value} style={{ flex: 1, height: 4, borderRadius: 2, background: step >= value ? '#E8123C' : '#26262e' }} />
      ))}
    </div>
  )
}

function InlineError({ error }) {
  if (!error) return null
  return <p role="alert" style={{ color: '#F4788F', fontSize: 13.5, margin: '0 0 16px' }}>{error}</p>
}

function ChoiceButton({ active, children, ...props }) {
  return (
    <button
      type="button"
      className="btn chip"
      aria-pressed={active}
      style={{
        padding: '9px 16px', borderRadius: 20, fontSize: 14, fontWeight: 650,
        background: active ? '#E8123C' : '#15151A', color: active ? '#fff' : '#b4b4be',
        border: active ? '1px solid #E8123C' : '1px solid rgba(255,255,255,.12)',
      }}
      {...props}
    >
      {children}
    </button>
  )
}

export default function Onboarding({ onFinish }) {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [nickname, setNickname] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('')
  const [interests, setInterests] = useState([])
  const [nicknameVerified, setNicknameVerified] = useState(false)
  const [checkingNickname, setCheckingNickname] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const cardStyle = active => ({
    flex: 1, textAlign: 'left', border: `1px solid ${active ? '#E8123C' : 'rgba(255,255,255,.12)'}`,
    borderRadius: 14, padding: '16px 20px', cursor: 'pointer', color: '#ECECEF',
    background: active ? 'rgba(232,18,60,.08)' : '#15151A', fontWeight: 700,
  })

  const verifyNickname = async () => {
    const name = nickname.trim()
    if (!name) {
      setError('닉네임을 입력해 주세요')
      return
    }
    setCheckingNickname(true)
    setError('')
    try {
      const result = await checkNickname(name)
      if (!result.available) {
        setNicknameVerified(false)
        setError('이미 사용 중인 닉네임입니다')
        return
      }
      setNicknameVerified(true)
    } catch (err) {
      setNicknameVerified(false)
      setError(err?.message || '닉네임 중복 확인에 실패했습니다')
    } finally {
      setCheckingNickname(false)
    }
  }

  const nextFromCredentials = () => {
    if (!nickname.trim()) return setError('닉네임을 입력해 주세요')
    const missing = passwordMissing(password)
    if (missing.length) {
      return setError(`비밀번호는 영문과 숫자를 포함한 8자 이상이어야 합니다 (부족: ${missing.join(', ')})`)
    }
    if (!nicknameVerified) return setError('닉네임 중복 확인을 완료해 주세요')
    if (!role) return setError('역할을 선택해 주세요')
    setError('')
    setStep(2)
  }

  const nextFromInterests = () => {
    if (interests.length === 0) {
      setError('관심사를 한 개 이상 선택해 주세요')
      return
    }
    setError('')
    setStep(3)
  }

  const toggleInterest = item => {
    setInterests(current => current.includes(item) ? current.filter(value => value !== item) : [...current, item])
    setError('')
  }

  const finish = async () => {
    if (submitting) return
    setSubmitting(true)
    setError('')
    try {
      await onFinish({ name: nickname.trim(), password, role, interests })
      setStep(4)
    } catch (err) {
      setError(err?.message || '회원가입에 실패했습니다. 다시 시도해 주세요.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main style={{ padding: '48px 40px 64px', maxWidth: 560, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 32, justifyContent: 'center' }}>
        <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#E8123C' }} />
        <span style={{ fontSize: 20, fontWeight: 800, color: '#fff' }}>EDU.AI</span>
      </div>
      <ProgressBar step={step} />

      {step === 1 && (
        <section>
          <h1 style={{ color: '#fff', fontSize: 27, margin: '0 0 8px' }}>회원가입</h1>
          <p style={{ color: '#9a9aa4', margin: '0 0 26px' }}>나에게 맞는 콘텐츠를 추천받을 정보를 등록해 주세요.</p>

          <label htmlFor="signup-nickname" style={{ display: 'block', color: '#9a9aa4', marginBottom: 8 }}>닉네임</label>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <input
              id="signup-nickname" value={nickname} placeholder="예) 김크레딧" autoComplete="username"
              onChange={event => { setNickname(event.target.value); setNicknameVerified(false); setError('') }}
              style={inputStyle}
            />
            <button type="button" className="btn" onClick={verifyNickname} disabled={checkingNickname} style={{ flexShrink: 0, padding: '0 16px', borderRadius: 10, background: '#26262e', color: '#fff' }}>
              {checkingNickname ? '확인 중...' : '중복 확인'}
            </button>
          </div>
          {nicknameVerified && <p style={{ color: '#48B982', fontSize: 13, margin: '0 0 15px' }}>사용 가능한 닉네임입니다</p>}

          <label htmlFor="signup-password" style={{ display: 'block', color: '#9a9aa4', margin: '15px 0 8px' }}>비밀번호</label>
          <input id="signup-password" aria-label="비밀번호" type="password" value={password} autoComplete="new-password" placeholder="영문·숫자 포함 8자 이상" onChange={event => { setPassword(event.target.value); setError('') }} style={{ ...inputStyle, marginBottom: 22 }} />

          <p style={{ color: '#9a9aa4', fontSize: 14, marginBottom: 10 }}>역할</p>
          <div role="radiogroup" aria-label="역할" style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
            {ROLE_OPTIONS.map(item => (
              <button key={item} type="button" role="radio" aria-label={item} aria-checked={role === item} onClick={() => { setRole(item); setError('') }} style={cardStyle(role === item)}>
                {item === '기획자' ? '🧭 ' : '⌨️ '}{item}
              </button>
            ))}
          </div>
          <InlineError error={error} />
          <button className="btn" onClick={nextFromCredentials} style={{ width: '100%', padding: 13, borderRadius: 12, background: '#E8123C', color: '#fff', fontWeight: 700 }}>다음</button>
        </section>
      )}

      {step === 2 && (
        <section>
          <h1 style={{ color: '#fff', fontSize: 27, margin: '0 0 8px' }}>관심사를 선택해 주세요</h1>
          <p style={{ color: '#9a9aa4', margin: '0 0 24px' }}>한 건 이상 선택해야 하며 여러 건 선택할 수 있습니다.</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 9, marginBottom: 26 }}>
            {INTEREST_OPTIONS.map(item => <ChoiceButton key={item} active={interests.includes(item)} onClick={() => toggleInterest(item)}>{item}</ChoiceButton>)}
          </div>
          <InlineError error={error} />
          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn" onClick={() => { setError(''); setStep(1) }} style={{ flex: 1, borderRadius: 12, background: '#15151A', color: '#fff' }}>이전</button>
            <button className="btn" onClick={nextFromInterests} style={{ flex: 2, padding: 13, borderRadius: 12, background: '#E8123C', color: '#fff', fontWeight: 700 }}>다음</button>
          </div>
        </section>
      )}

      {step === 3 && (
        <section>
          <h1 style={{ color: '#fff', fontSize: 27, margin: '0 0 8px' }}>가입 정보를 확인해 주세요</h1>
          <p style={{ color: '#9a9aa4', margin: '0 0 24px' }}>선택한 역할과 관심사는 내 정보에서 언제든 수정할 수 있습니다.</p>
          <div style={{ padding: 22, borderRadius: 16, background: '#15151A', border: '1px solid rgba(255,255,255,.1)', marginBottom: 22 }}>
            <p style={{ color: '#7a7a84', fontSize: 13, margin: '0 0 8px' }}>역할</p>
            <span style={{ display: 'inline-block', padding: '7px 14px', borderRadius: 18, background: '#E8123C', color: '#fff', fontWeight: 700, marginBottom: 20 }}>{role}</span>
            <p style={{ color: '#7a7a84', fontSize: 13, margin: '0 0 8px' }}>관심사</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {interests.map(item => <span key={item} style={{ padding: '7px 13px', borderRadius: 18, background: 'rgba(232,18,60,.12)', border: '1px solid #E8123C', color: '#fff' }}>{item}</span>)}
            </div>
          </div>
          <InlineError error={error} />
          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn" onClick={() => setStep(2)} style={{ flex: 1, borderRadius: 12, background: '#15151A', color: '#fff' }}>이전</button>
            <button className="btn" onClick={finish} disabled={submitting} style={{ flex: 2, padding: 13, borderRadius: 12, background: '#E8123C', color: '#fff', fontWeight: 700 }}>{submitting ? '가입 중...' : '회원가입'}</button>
          </div>
        </section>
      )}

      {step === 4 && (
        <section style={{ textAlign: 'center', padding: '24px 0' }}>
          <div style={{ fontSize: 50, marginBottom: 18 }}>🎉</div>
          <h1 style={{ color: '#fff', fontSize: 28, margin: '0 0 10px' }}>회원가입을 축하합니다!</h1>
          <p style={{ color: '#9a9aa4', margin: '0 0 28px' }}>{nickname}님, EDU.AI에서 새로운 인사이트를 만나보세요.</p>
          <button className="btn" onClick={() => navigate('/')} style={{ width: '100%', padding: 13, borderRadius: 12, background: '#E8123C', color: '#fff', fontWeight: 700 }}>홈으로 가기</button>
        </section>
      )}
    </main>
  )
}
