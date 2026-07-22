import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  deleteCurrentMember,
  fetchCurrentMember,
  logoutMember,
  updateCurrentMember,
} from '../api/client'
import { INTEREST_OPTIONS, ROLE_OPTIONS } from '../data/authOptions'

function formatDate(value) {
  if (!value) return ''
  const date = new Date(value)
  return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`
}

const chipStyle = active => ({
  padding: '8px 16px', borderRadius: 20, fontSize: 13.5, fontWeight: 650,
  background: active ? '#E8123C' : '#15151A', color: active ? '#fff' : '#b4b4be',
  border: active ? '1px solid #E8123C' : '1px solid rgba(255,255,255,.12)',
})

export default function Profile({ user, setUser }) {
  const navigate = useNavigate()
  const [member, setMember] = useState(null)
  const [role, setRole] = useState('')
  const [interests, setInterests] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [withdrawOpen, setWithdrawOpen] = useState(false)

  useEffect(() => {
    if (!user) {
      navigate('/', { replace: true })
      return
    }
    let active = true
    fetchCurrentMember()
      .then(current => {
        if (!active) return
        setMember(current)
        setRole(current.role || '')
        setInterests(Array.isArray(current.interests) ? current.interests : [])
      })
      .catch(() => {
        if (!active) return
        setUser(null)
        navigate('/', { replace: true })
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [navigate, setUser, user])

  const toggleInterest = item => {
    setInterests(current => current.includes(item) ? current.filter(value => value !== item) : [...current, item])
    setError('')
    setMessage('')
  }

  const save = async () => {
    if (interests.length === 0) {
      setError('관심사를 한 개 이상 선택해 주세요')
      return
    }
    if (!role) {
      setError('역할을 선택해 주세요')
      return
    }
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const updated = await updateCurrentMember({ role, interests })
      setMember(updated)
      setRole(updated.role)
      setInterests(updated.interests)
      setUser(updated)
      setMessage('저장되었습니다.')
    } catch (err) {
      setError(err?.message || '저장에 실패했습니다')
    } finally {
      setSaving(false)
    }
  }

  const clearBrowserUserData = () => {
    localStorage.removeItem('nexus.user')
    localStorage.removeItem('nexus.enrolled')
  }

  const logout = async () => {
    setError('')
    try {
      await logoutMember()
      clearBrowserUserData()
      setUser(null)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err?.message || '로그아웃에 실패했습니다')
    }
  }

  const withdraw = async () => {
    setError('')
    try {
      await deleteCurrentMember()
      clearBrowserUserData()
      setUser(null)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err?.message || '탈회에 실패했습니다')
      setWithdrawOpen(false)
    }
  }

  if (!user) return null
  if (loading) return <main style={{ padding: 60, textAlign: 'center', color: '#9a9aa4' }}>회원 정보를 불러오는 중...</main>
  if (!member) return null

  return (
    <main style={{ padding: '42px 40px 80px', maxWidth: 680, margin: '0 auto' }}>
      <p style={{ color: '#E8123C', fontSize: 11, fontFamily: 'monospace', letterSpacing: '.06em', margin: '0 0 10px' }}>NEXUS · MY PROFILE</p>
      <h1 style={{ color: '#fff', fontSize: 29, margin: '0 0 32px' }}>내 정보</h1>

      <section style={{ padding: 22, background: '#15151A', border: '1px solid rgba(255,255,255,.09)', borderRadius: 16, marginBottom: 24 }}>
        <p style={{ color: '#7a7a84', fontSize: 13, margin: '0 0 6px' }}>닉네임</p>
        <p style={{ color: '#fff', fontSize: 18, fontWeight: 750, margin: '0 0 18px' }}>{member.nickname}</p>
        <p style={{ color: '#7a7a84', fontSize: 13, margin: '0 0 6px' }}>가입일</p>
        <p style={{ color: '#dcdce2', margin: 0 }}>{formatDate(member.createdAt)}</p>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h2 style={{ color: '#fff', fontSize: 16, margin: '0 0 12px' }}>역할</h2>
        <div style={{ display: 'flex', gap: 10 }}>
          {ROLE_OPTIONS.map(item => (
            <button key={item} className="btn" aria-pressed={role === item} onClick={() => { setRole(item); setError(''); setMessage('') }} style={chipStyle(role === item)}>{item}</button>
          ))}
        </div>
      </section>

      <section style={{ marginBottom: 28 }}>
        <h2 style={{ color: '#fff', fontSize: 16, margin: '0 0 7px' }}>관심사</h2>
        <p style={{ color: '#7a7a84', fontSize: 13, margin: '0 0 12px' }}>한 건 이상, 여러 건 선택할 수 있습니다.</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {INTEREST_OPTIONS.map(item => (
            <button key={item} className="btn" aria-pressed={interests.includes(item)} onClick={() => toggleInterest(item)} style={chipStyle(interests.includes(item))}>{item}</button>
          ))}
        </div>
      </section>

      {message && <p role="status" style={{ color: '#48B982', fontSize: 14 }}>{message}</p>}
      {error && <p role="alert" style={{ color: '#F4788F', fontSize: 14 }}>{error}</p>}
      <button className="btn" onClick={save} disabled={saving} style={{ width: '100%', padding: 13, borderRadius: 12, background: '#E8123C', color: '#fff', fontWeight: 700, marginBottom: 32 }}>{saving ? '저장 중...' : '저장'}</button>

      <div style={{ borderTop: '1px solid rgba(255,255,255,.08)', paddingTop: 24, display: 'flex', gap: 10, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <button className="btn" onClick={logout} style={{ padding: '11px 22px', borderRadius: 12, background: '#15151A', color: '#dcdce2', border: '1px solid rgba(255,255,255,.12)' }}>로그아웃</button>
        {!withdrawOpen && <button className="btn" onClick={() => setWithdrawOpen(true)} style={{ padding: '11px 22px', borderRadius: 12, background: 'none', color: '#7a7a84', border: '1px solid rgba(255,255,255,.08)' }}>탈회</button>}
      </div>

      {withdrawOpen && (
        <section style={{ marginTop: 16, padding: 20, borderRadius: 14, background: '#15151A', border: '1px solid rgba(232,18,60,.35)' }}>
          <p style={{ color: '#F4788F', margin: '0 0 16px' }}>작성한 글과 댓글은 남지만 계정과 좋아요는 삭제됩니다. 되돌릴 수 없습니다.</p>
          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn" onClick={withdraw} style={{ padding: '10px 18px', borderRadius: 10, background: '#E8123C', color: '#fff', fontWeight: 700 }}>정말 탈회하기</button>
            <button className="btn" onClick={() => setWithdrawOpen(false)} style={{ padding: '10px 18px', borderRadius: 10, background: '#26262e', color: '#fff' }}>취소</button>
          </div>
        </section>
      )}
    </main>
  )
}
