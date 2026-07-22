import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import BackLink from '../components/BackLink'
import { createPost } from '../api/client'

const ALLOWED_TAGS = ['자료', '노하우', '팁', '기술자료']

export default function CommunityWrite({ user }) {
  const navigate = useNavigate()
  const [tag, setTag] = useState(ALLOWED_TAGS[0])
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!user || typeof user !== 'object' || !user.id) {
      navigate('/onboarding', { replace: true })
    }
  }, [user, navigate])

  if (!user || typeof user !== 'object' || !user.id) return null

  const handleSubmit = async () => {
    if (!title.trim() || !body.trim()) {
      setError('제목과 본문을 입력해주세요.')
      return
    }
    setSubmitting(true)
    setError(null)

    try {
      const post = await createPost({ memberId: user.id, tag, title: title.trim(), body: body.trim() })
      navigate(`/community/${post.id}`)
    } catch (err) {
      setError(err.message)
      setSubmitting(false)
    }
  }

  const inputStyle = {
    width: '100%', background: '#15151A',
    border: '1px solid rgba(255,255,255,.12)', borderRadius: 10,
    padding: '12px 14px', fontSize: 15, color: '#ECECEF',
    fontFamily: 'inherit', outline: 'none',
    boxSizing: 'border-box',
  }

  return (
    <main style={{ padding: '40px 40px 64px', maxWidth: 720, margin: '0 auto' }}>
      <BackLink to="/community" bottomGap={24}>← 커뮤니티</BackLink>

      <p style={{
        fontFamily: '"JetBrains Mono", monospace',
        fontSize: 11, fontWeight: 600, letterSpacing: '.06em',
        color: '#E8123C', margin: '0 0 10px',
      }}>
        COMMUNITY · 새 글 작성
      </p>
      <h1 style={{ fontSize: 28, fontWeight: 800, color: '#fff', letterSpacing: '-.03em', margin: '0 0 32px' }}>
        글쓰기
      </h1>

      {/* Tag selector */}
      <div style={{ marginBottom: 24 }}>
        <p style={{ fontSize: 14, color: '#9a9aa4', margin: '0 0 10px' }}>태그 선택</p>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {ALLOWED_TAGS.map(t => (
            <button
              key={t}
              className="btn chip"
              onClick={() => setTag(t)}
              aria-pressed={tag === t}
              style={{
                padding: '7px 16px', borderRadius: 20, fontSize: 13.5, fontWeight: 600,
                background: tag === t ? '#E8123C' : '#15151A',
                color: tag === t ? '#fff' : '#b4b4be',
                border: tag === t ? '1px solid #E8123C' : '1px solid rgba(255,255,255,.12)',
              }}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Title */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', fontSize: 14, color: '#9a9aa4', marginBottom: 8 }}>제목</label>
        <input
          placeholder="제목을 입력해주세요"
          value={title}
          onChange={e => setTitle(e.target.value)}
          style={inputStyle}
        />
      </div>

      {/* Body */}
      <div style={{ marginBottom: 24 }}>
        <label style={{ display: 'block', fontSize: 14, color: '#9a9aa4', marginBottom: 8 }}>본문</label>
        <textarea
          placeholder="본문을 입력해주세요"
          value={body}
          onChange={e => setBody(e.target.value)}
          rows={12}
          style={{
            ...inputStyle,
            resize: 'vertical',
            lineHeight: 1.7,
          }}
        />
      </div>

      {/* Error */}
      {error && (
        <p style={{ fontSize: 14, color: '#F4788F', margin: '0 0 16px' }}>{error}</p>
      )}

      {/* Submit */}
      <button
        className="btn"
        onClick={handleSubmit}
        disabled={submitting}
        style={{
          background: submitting ? '#7a0a22' : '#E8123C', color: '#fff',
          fontSize: 15, fontWeight: 700,
          padding: '13px 32px', borderRadius: 12,
          opacity: submitting ? 0.7 : 1,
        }}
      >
        {submitting ? '등록 중...' : '등록'}
      </button>
    </main>
  )
}
