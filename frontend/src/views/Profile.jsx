import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchMember, updateMember, deleteMember, registerMember } from '../api/client'

const ROLES = ['직장인', '개발자']
const INTERESTS_OPTIONS = ['데이터 분석', 'LLM·생성형 AI', '금융 도메인', '생산성', '커리어', 'MLOps']

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}.${m}.${day}`
}

function parseInterests(raw) {
  if (!raw) return []
  return raw.split(',').map(s => s.trim()).filter(Boolean)
}

const inputStyle = {
  width: '100%', background: '#15151A',
  border: '1px solid rgba(255,255,255,.12)', borderRadius: 10,
  padding: '12px 14px', fontSize: 15, color: '#ECECEF',
  fontFamily: 'inherit', outline: 'none',
  boxSizing: 'border-box',
}

const labelStyle = {
  display: 'block', fontSize: 14, color: '#9a9aa4', marginBottom: 8,
}

export default function Profile({ user, setUser }) {
  const navigate = useNavigate()
  const [member, setMember] = useState(null)
  const [loading, setLoading] = useState(true)
  const [nickname, setNickname] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('')
  const [interests, setInterests] = useState([])
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState(null)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [withdrawStep, setWithdrawStep] = useState(0)

  useEffect(() => {
    if (!user) {
      navigate('/onboarding', { replace: true })
      return
    }

    const loadMember = async () => {
      let userId = typeof user === 'object' ? user.id : null

      if (!userId && typeof user === 'string') {
        try {
          const m = await registerMember({ nickname: user })
          setUser({ id: m.id, nickname: m.nickname, role: m.role })
          userId = m.id
        } catch {
          navigate('/onboarding', { replace: true })
          return
        }
      }

      if (!userId) {
        navigate('/onboarding', { replace: true })
        return
      }

      try {
        const m = await fetchMember(userId)
        setMember(m)
        setNickname(m.nickname || '')
        setEmail(m.email || '')
        setRole(m.role || '')
        setInterests(parseInterests(m.interests))
      } catch {
        navigate('/onboarding', { replace: true })
      } finally {
        setLoading(false)
      }
    }

    loadMember()
  }, [user, navigate, setUser])

  if (!user) return null
  if (loading) return <main style={{ padding: '60px 40px', color: '#9a9aa4', textAlign: 'center' }}>불러오는 중...</main>
  if (!member) return null

  const toggleInterest = (item) => {
    setInterests(prev =>
      prev.includes(item) ? prev.filter(i => i !== item) : [...prev, item]
    )
  }

  const handleSave = async () => {
    setSaving(true)
    setSaveError(null)
    setSaveSuccess(false)

    const patch = {}
    if (nickname !== member.nickname) patch.nickname = nickname
    if (!member.email && email) patch.email = email
    if (role !== (member.role || '')) patch.role = role
    const interestsStr = interests.join(', ')
    if (interestsStr !== (member.interests || '')) patch.interests = interestsStr

    if (Object.keys(patch).length === 0) {
      setSaving(false)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 2000)
      return
    }

    try {
      const updated = await updateMember(member.id, patch)
      setMember(updated)
      setNickname(updated.nickname || '')
      setEmail(updated.email || '')
      setRole(updated.role || '')
      setInterests(parseInterests(updated.interests))
      setUser({ id: updated.id, nickname: updated.nickname, role: updated.role })
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (err) {
      setSaveError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const clearLocalData = () => {
    // 같은 브라우저에서 다른 계정 사용 시 이전 사용자의 데이터가 남지 않도록 정리
    localStorage.removeItem('nexus.enrolled')
    localStorage.removeItem('nexus.comments')
  }

  const handleLogout = () => {
    clearLocalData()
    setUser(null)
    navigate('/')
  }

  const handleWithdrawConfirm = async () => {
    try {
      await deleteMember(member.id)
      clearLocalData()
      setUser(null)
      navigate('/')
    } catch (err) {
      setSaveError(err.message)
      setWithdrawStep(0)
    }
  }

  return (
    <main style={{ padding: '40px 40px 80px', maxWidth: 620, margin: '0 auto' }}>
      <p style={{
        fontFamily: '"JetBrains Mono", monospace',
        fontSize: 11, fontWeight: 600, letterSpacing: '.06em',
        color: '#E8123C', margin: '0 0 10px',
      }}>
        NEXUS · 마이페이지
      </p>
      <h1 style={{ fontSize: 28, fontWeight: 800, color: '#fff', letterSpacing: '-.03em', margin: '0 0 36px' }}>
        내 정보
      </h1>

      {/* 닉네임 */}
      <div style={{ marginBottom: 20 }}>
        <label style={labelStyle}>닉네임</label>
        <input
          value={nickname}
          onChange={e => setNickname(e.target.value)}
          style={inputStyle}
        />
        <p style={{ fontSize: 12.5, color: '#7a7a84', margin: '6px 0 0' }}>
          닉네임을 변경해도 기존에 작성한 글·댓글의 작성자명은 바뀌지 않아요
        </p>
      </div>

      {/* 이메일 */}
      <div style={{ marginBottom: 20 }}>
        <label style={labelStyle}>이메일</label>
        {member.email ? (
          <div style={{
            ...inputStyle,
            color: '#7a7a84',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <span>{member.email}</span>
            <span style={{ fontSize: 12, color: '#55555f' }}>수정 불가</span>
          </div>
        ) : (
          <div>
            <input
              type="email"
              placeholder="이메일 입력"
              value={email}
              onChange={e => setEmail(e.target.value)}
              style={inputStyle}
            />
            <p style={{ fontSize: 12, color: '#7a7a84', margin: '6px 0 0' }}>최초 1회만 등록할 수 있어요</p>
          </div>
        )}
      </div>

      {/* 역할 */}
      <div style={{ marginBottom: 20 }}>
        <label style={labelStyle}>역할</label>
        <div style={{ display: 'flex', gap: 10 }}>
          {ROLES.map(r => (
            <button
              key={r}
              className="btn chip"
              onClick={() => setRole(r)}
              aria-pressed={role === r}
              style={{
                padding: '8px 20px', borderRadius: 20, fontSize: 14, fontWeight: 600,
                background: role === r ? '#E8123C' : '#15151A',
                color: role === r ? '#fff' : '#b4b4be',
                border: role === r ? '1px solid #E8123C' : '1px solid rgba(255,255,255,.12)',
              }}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* 관심사 */}
      <div style={{ marginBottom: 20 }}>
        <label style={labelStyle}>관심사</label>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {INTERESTS_OPTIONS.map(item => {
            const active = interests.includes(item)
            return (
              <button
                key={item}
                className="btn chip"
                onClick={() => toggleInterest(item)}
                aria-pressed={active}
                style={{
                  padding: '7px 16px', borderRadius: 20, fontSize: 13.5, fontWeight: 600,
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
      </div>

      {/* 가입일 */}
      <div style={{ marginBottom: 32 }}>
        <label style={labelStyle}>가입일</label>
        <p style={{ fontSize: 15, color: '#ECECEF', margin: 0 }}>{formatDate(member.createdAt)}</p>
      </div>

      {/* 저장 피드백 */}
      {saveSuccess && (
        <p style={{ fontSize: 14, color: '#1F8A5B', margin: '0 0 12px' }}>저장되었습니다.</p>
      )}
      {saveError && (
        <p style={{ fontSize: 14, color: '#F4788F', margin: '0 0 12px' }}>{saveError}</p>
      )}

      {/* 저장 버튼 */}
      <button
        className="btn"
        onClick={handleSave}
        disabled={saving}
        style={{
          display: 'block',
          background: saving ? '#7a0a22' : '#E8123C', color: '#fff',
          fontSize: 15, fontWeight: 700,
          padding: '13px 32px', borderRadius: 12,
          opacity: saving ? 0.7 : 1,
          marginBottom: 32,
        }}
      >
        {saving ? '저장 중...' : '저장'}
      </button>

      <div style={{ borderTop: '1px solid rgba(255,255,255,.08)', marginBottom: 24 }} />

      {/* 로그아웃 */}
      <button
        className="btn"
        onClick={handleLogout}
        style={{
          background: '#15151A', color: '#dcdce2',
          fontSize: 14, fontWeight: 600,
          padding: '11px 24px', borderRadius: 12,
          border: '1px solid rgba(255,255,255,.12)',
          marginBottom: 16, marginRight: 12,
        }}
      >
        로그아웃
      </button>

      {/* 탈회 */}
      {withdrawStep === 0 ? (
        <button
          className="btn"
          onClick={() => setWithdrawStep(1)}
          style={{
            background: 'none', color: '#7a7a84',
            fontSize: 13.5, fontWeight: 500,
            padding: '11px 24px', borderRadius: 12,
            border: '1px solid rgba(255,255,255,.08)',
          }}
        >
          탈회
        </button>
      ) : (
        <div style={{
          background: '#15151A',
          border: '1px solid rgba(232,18,60,.3)',
          borderRadius: 14, padding: '20px',
          marginTop: 8,
        }}>
          <p style={{ fontSize: 14, color: '#F4788F', margin: '0 0 16px', lineHeight: 1.6 }}>
            작성한 글과 댓글은 남지만 계정과 좋아요는 삭제됩니다. 되돌릴 수 없습니다.
          </p>
          <div style={{ display: 'flex', gap: 10 }}>
            <button
              className="btn"
              onClick={handleWithdrawConfirm}
              style={{
                background: '#E8123C', color: '#fff',
                fontSize: 14, fontWeight: 700,
                padding: '10px 20px', borderRadius: 10,
              }}
            >
              정말 탈회하기
            </button>
            <button
              className="btn"
              onClick={() => setWithdrawStep(0)}
              style={{
                background: '#15151A', color: '#dcdce2',
                fontSize: 14, fontWeight: 600,
                padding: '10px 20px', borderRadius: 10,
                border: '1px solid rgba(255,255,255,.12)',
              }}
            >
              취소
            </button>
          </div>
        </div>
      )}
    </main>
  )
}
