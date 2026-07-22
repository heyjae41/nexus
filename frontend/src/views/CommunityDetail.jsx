import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { fetchPost, createComment, likePost } from '../api/client'
import { communityAvatarGrad, fmtKo, initial } from '../utils/grads'
import { timeAgo } from '../utils/timeAgo'

export default function CommunityDetail({ user }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const commentRef = useRef()
  const likeInFlight = useRef(false)

  const [post, setPost] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [liked, setLiked] = useState(false)
  const [commentError, setCommentError] = useState(null)
  const [likeCount, setLikeCount] = useState(0)

  const loadPost = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchPost(id)
      setPost(data)
      setLikeCount(data.likesCount ?? 0)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { loadPost() }, [loadPost])


  const handleLike = async () => {
    if (likeInFlight.current) return
    if (!user) { navigate('/onboarding'); return }
    likeInFlight.current = true
    const nextLiked = !liked
    setLiked(nextLiked)
    setLikeCount(v => nextLiked ? v + 1 : v - 1)
    try {
      const data = await likePost(id, user.id)
      if (data?.likesCount !== undefined) setLikeCount(data.likesCount)
      if (data?.liked !== undefined) setLiked(data.liked)
    } catch {
      setLiked(!nextLiked)
      setLikeCount(v => nextLiked ? v - 1 : v + 1)
    } finally {
      likeInFlight.current = false
    }
  }

  const handleAddComment = async () => {
    const val = commentRef.current?.value?.trim()
    if (!val || !user) return

    try {
      await createComment(id, { memberId: user.id, body: val })
      commentRef.current.value = ''
      setCommentError(null)
      await loadPost()
    } catch (err) {
      setCommentError(err.message || '댓글 등록에 실패했습니다')
    }
  }

  const actionBtn = (active) => ({
    display: 'flex', alignItems: 'center', gap: 7,
    padding: '9px 18px', borderRadius: 24,
    fontSize: 14, fontWeight: 600, cursor: 'pointer', border: 'none',
    fontFamily: 'inherit',
    background: active ? 'rgba(232,18,60,.14)' : 'rgba(255,255,255,.05)',
    color: active ? '#F4788F' : '#c9c9d2',
    transition: 'all .15s',
  })

  if (loading) {
    return (
      <main style={{ padding: '40px 40px 64px', maxWidth: 720, margin: '0 auto' }}>
        <p style={{ color: '#9a9aa4', fontSize: 14 }}>불러오는 중...</p>
      </main>
    )
  }

  if (error || !post) {
    return (
      <main style={{ padding: '40px 40px 64px', maxWidth: 720, margin: '0 auto' }}>
        <p style={{ color: '#9a9aa4', fontSize: 14 }}>글을 찾을 수 없습니다.</p>
      </main>
    )
  }

  const grad = communityAvatarGrad(0)
  const bodyParagraphs = (post.body || '').split('\n').filter(Boolean)

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
          {initial(post.authorName)}
        </div>
        <div>
          <span style={{ fontSize: 14, fontWeight: 700, color: '#ECECEF' }}>{post.authorName}</span>
          <span style={{ fontSize: 12.5, color: '#7a7a84', marginLeft: 8 }}>
            #{post.tag} · {timeAgo(post.createdAt)}
          </span>
        </div>
      </div>

      <h1 style={{ fontSize: 26, fontWeight: 800, color: '#fff', lineHeight: 1.35, letterSpacing: '-.02em', margin: '0 0 20px' }}>
        {post.title}
      </h1>

      {/* Body — plain text paragraphs, no dangerouslySetInnerHTML */}
      <div style={{ marginBottom: 28 }}>
        {bodyParagraphs.map((para, i) => (
          <p key={i} style={{ fontSize: 16, lineHeight: 1.85, color: '#cacad2', margin: '0 0 12px' }}>
            {para}
          </p>
        ))}
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 32, flexWrap: 'wrap' }}>
        <button className="btn actn" style={actionBtn(liked)} onClick={handleLike}>
          ♥ 좋아요 {fmtKo(likeCount)}
        </button>
        <button className="btn actn" style={actionBtn(false)}>🔖 저장</button>
        <div style={{ flex: 1 }} />
        <button className="btn actn" style={actionBtn(false)}>↗ 공유</button>
      </div>

      {/* Comments */}
      <div style={{ borderTop: '1px solid rgba(255,255,255,.08)', paddingTop: 28 }}>
        <p style={{ fontSize: 16, fontWeight: 700, color: '#ECECEF', margin: '0 0 18px' }}>
          댓글 {(post.comments || []).length}
        </p>

        {/* Comment input */}
        {user ? (
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
            {commentError && (
              <p style={{ color: '#E8123C', fontSize: 13, margin: '8px 0 0' }}>{commentError}</p>
            )}
          </div>
        ) : (
          <p
            onClick={() => navigate('/onboarding')}
            style={{ fontSize: 14, color: '#7a7a84', margin: '0 0 24px', cursor: 'pointer' }}
          >
            로그인 후 댓글을 쓸 수 있어요
          </p>
        )}

        {/* Comment list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          {(post.comments || []).map((c, i) => (
            <div key={c.id ?? i} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
              <div style={{
                width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
                background: '#26262e',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 13, fontWeight: 700, color: '#fff',
              }}>
                {initial(c.authorName)}
              </div>
              <div>
                <p style={{ fontSize: 13.5, fontWeight: 700, color: '#ECECEF', margin: '0 0 4px' }}>{c.authorName}</p>
                <p style={{ fontSize: 14, color: '#b4b4be', margin: 0, lineHeight: 1.6 }}>{c.body}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </main>
  )
}
