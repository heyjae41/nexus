import { useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { POSTS, getDefaultComments } from '../data'
import { communityAvatarGrad, fmtKo, initial } from '../utils/grads'

export default function CommunityDetail({ user, comments, onAddComment }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const commentRef = useRef()
  const post = POSTS.find(p => p.id === id)
  const [localLikes, setLocalLikes] = useState(post?.likes || 0)
  const [liked, setLiked] = useState(false)

  if (!post) return <div style={{ padding: 40, color: '#9a9aa4' }}>글을 찾을 수 없습니다.</div>

  const allComments = [...getDefaultComments(id), ...(comments?.[id] || [])]
  const grad = communityAvatarGrad(POSTS.indexOf(post))

  const handleLike = () => {
    setLiked(v => !v)
    setLocalLikes(v => liked ? v - 1 : v + 1)
  }

  const handleAddComment = () => {
    const val = commentRef.current?.value?.trim()
    if (!val) return
    onAddComment(id, val)
    commentRef.current.value = ''
  }

  const actionBtn = (label, active, onClick) => ({
    display: 'flex', alignItems: 'center', gap: 7,
    padding: '9px 18px', borderRadius: 24,
    fontSize: 14, fontWeight: 600, cursor: 'pointer', border: 'none',
    fontFamily: 'inherit',
    background: active ? 'rgba(232,18,60,.14)' : 'rgba(255,255,255,.05)',
    color: active ? '#F4788F' : '#c9c9d2',
    transition: 'all .15s',
  })

  return (
    <main style={{ padding: '40px 40px 64px', maxWidth: 720, margin: '0 auto' }}>
      <button
        className="back-link btn"
        onClick={() => navigate('/community')}
        style={{ background: 'none', border: 'none', color: '#8a8a94', fontSize: 13.5, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, padding: '0 0 20px' }}
      >
        ← 커뮤니티
      </button>

      {/* Author row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <div style={{
          width: 46, height: 46, borderRadius: '50%',
          background: grad,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 17, fontWeight: 800, color: '#fff', flexShrink: 0,
        }}>
          {initial(post.author)}
        </div>
        <div>
          <span style={{ fontSize: 14, fontWeight: 700, color: '#ECECEF' }}>{post.author}</span>
          <span style={{ fontSize: 12.5, color: '#7a7a84', marginLeft: 8 }}>#{post.tag} · {post.time}</span>
        </div>
      </div>

      <h1 style={{ fontSize: 26, fontWeight: 800, color: '#fff', lineHeight: 1.35, letterSpacing: '-.02em', margin: '0 0 20px' }}>
        {post.title}
      </h1>

      <p style={{ fontSize: 16, lineHeight: 1.85, color: '#cacad2', margin: '0 0 28px', whiteSpace: 'pre-line' }}>
        {post.body}
      </p>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 32, flexWrap: 'wrap' }}>
        <button className="btn actn" style={actionBtn('♥', liked)} onClick={handleLike}>
          ♥ 좋아요 {fmtKo(localLikes)}
        </button>
        <button className="btn actn" style={actionBtn('🔖', false)}>🔖 저장</button>
        <div style={{ flex: 1 }} />
        <button className="btn actn" style={actionBtn('↗', false)}>↗ 공유</button>
      </div>

      {/* Comments */}
      <div style={{ borderTop: '1px solid rgba(255,255,255,.08)', paddingTop: 28 }}>
        <p style={{ fontSize: 16, fontWeight: 700, color: '#ECECEF', margin: '0 0 18px' }}>
          댓글 {allComments.length}
        </p>

        {/* Comment input */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 24 }}>
          <input
            ref={commentRef}
            placeholder="댓글을 남겨보세요"
            onKeyDown={e => e.key === 'Enter' && handleAddComment()}
            style={{
              flex: 1, background: '#15151A',
              border: '1px solid rgba(255,255,255,.12)',
              borderRadius: 10, padding: '11px 14px',
              fontSize: 14, color: '#ECECEF',
              fontFamily: 'inherit', outline: 'none',
            }}
          />
          <button
            className="btn"
            onClick={handleAddComment}
            style={{
              background: '#E8123C', color: '#fff',
              fontSize: 14, fontWeight: 700,
              padding: '0 18px', borderRadius: 10,
            }}
          >
            등록
          </button>
        </div>

        {/* Comment list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          {allComments.map((c, i) => (
            <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
              <div style={{
                width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
                background: '#26262e',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 13, fontWeight: 700, color: '#fff',
              }}>
                {initial(c.a)}
              </div>
              <div>
                <p style={{ fontSize: 13.5, fontWeight: 700, color: '#ECECEF', margin: '0 0 4px' }}>{c.a}</p>
                <p style={{ fontSize: 14, color: '#b4b4be', margin: 0, lineHeight: 1.6 }}>{c.t}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </main>
  )
}
