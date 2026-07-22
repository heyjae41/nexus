import { useRef, useState } from 'react'
import { loginMember } from '../api/client'
import { useModalA11y } from '../hooks/useModalA11y'

const inputStyle = {
  width: '100%', boxSizing: 'border-box', padding: '12px 14px',
  borderRadius: 10, border: '1px solid rgba(255,255,255,.12)',
  background: '#15151A', color: '#ECECEF', fontSize: 15,
}

export default function AuthModal({ open, onClose, onAuthenticated, onSignup }) {
  const [nickname, setNickname] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const dialogRef = useRef(null)
  const nicknameRef = useRef(null)

  useModalA11y({ active: open, containerRef: dialogRef, onClose, initialFocusRef: nicknameRef })

  if (!open) return null

  const submit = async (event) => {
    event.preventDefault()
    if (!nickname.trim() || !password) {
      setError('닉네임과 비밀번호를 입력해 주세요')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      const member = await loginMember({ nickname: nickname.trim(), password })
      onAuthenticated(member)
      onClose()
    } catch (err) {
      setError(err?.message || '로그인에 실패했습니다')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 100,
        display: 'grid', placeItems: 'center', padding: 20,
        background: 'rgba(0,0,0,.72)', backdropFilter: 'blur(5px)',
      }}
      onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}
    >
      <section
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="login-title"
        style={{
          width: '100%', maxWidth: 420, padding: 28,
          borderRadius: 18, background: '#101015',
          border: '1px solid rgba(255,255,255,.12)',
          boxShadow: '0 24px 70px rgba(0,0,0,.55)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <h1 id="login-title" style={{ margin: 0, color: '#fff', fontSize: 24 }}>로그인</h1>
          <button className="btn" aria-label="로그인 창 닫기" onClick={onClose} style={{ background: 'none', color: '#9a9aa4', fontSize: 22 }}>×</button>
        </div>

        <form onSubmit={submit}>
          <label htmlFor="login-nickname" style={{ display: 'block', color: '#9a9aa4', fontSize: 14, marginBottom: 8 }}>닉네임</label>
          <input ref={nicknameRef} id="login-nickname" value={nickname} onChange={event => setNickname(event.target.value)} autoComplete="username" style={{ ...inputStyle, marginBottom: 16 }} />

          <label htmlFor="login-password" style={{ display: 'block', color: '#9a9aa4', fontSize: 14, marginBottom: 8 }}>비밀번호</label>
          <input id="login-password" type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="current-password" style={{ ...inputStyle, marginBottom: 10 }} />

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 20 }}>
            <span style={{ color: '#9a9aa4', fontSize: 13 }}>처음이시라면 회원가입을 해주세요</span>
            <button type="button" className="btn" onClick={onSignup} style={{ background: 'none', color: '#F4788F', fontWeight: 700, padding: 4 }}>회원가입</button>
          </div>

          {error && <p role="alert" style={{ color: '#F4788F', fontSize: 13.5, margin: '0 0 14px' }}>{error}</p>}
          <button type="submit" className="btn" disabled={submitting} style={{ width: '100%', padding: '13px 0', borderRadius: 12, background: '#E8123C', color: '#fff', fontWeight: 700 }}>
            {submitting ? '로그인 중...' : '로그인'}
          </button>
        </form>
      </section>
    </div>
  )
}
