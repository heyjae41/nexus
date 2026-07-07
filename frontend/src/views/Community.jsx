import { useNavigate } from 'react-router-dom'
import { POSTS } from '../data'
import { communityAvatarGrad, fmtKo, initial } from '../utils/grads'

function PostCard({ post, index, onClick }) {
  const grad = communityAvatarGrad(index)
  return (
    <div
      className="card"
      onClick={onClick}
      style={{
        display: 'flex', gap: 14, alignItems: 'flex-start',
        background: '#15151A', border: '1px solid rgba(255,255,255,.06)',
        borderRadius: 14, padding: '16px 18px',
      }}
    >
      <div style={{
        width: 46, height: 46, borderRadius: '50%', flexShrink: 0,
        background: grad,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 17, fontWeight: 800, color: '#fff',
      }}>
        {initial(post.author)}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
          <span className="tagchip" style={{
            fontFamily: '"JetBrains Mono", monospace',
            fontSize: 10.5, fontWeight: 600, letterSpacing: '.03em',
            color: '#E8123C',
            background: 'rgba(232,18,60,.12)',
            border: '1px solid rgba(232,18,60,.2)',
            padding: '2px 8px', borderRadius: 5,
            transition: 'all .15s',
          }}>
            {post.tag}
          </span>
          <span style={{ fontSize: 12.5, color: '#7a7a84' }}>
            {post.author} · {post.time}
          </span>
        </div>
        <p style={{ fontSize: 17, fontWeight: 700, color: '#ECECEF', lineHeight: 1.4, margin: '0 0 8px' }}>
          {post.title}
        </p>
        <p style={{ fontSize: 12.5, color: '#7a7a84', margin: 0 }}>
          ♥ {fmtKo(post.likes)} · 💬 {post.commentCount}
        </p>
      </div>
    </div>
  )
}

export default function Community({ user: _user }) {
  const navigate = useNavigate()

  return (
    <main style={{ padding: '40px 40px 64px', maxWidth: 820, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12, gap: 16 }}>
        <div>
          <p style={{
            fontFamily: '"JetBrains Mono", monospace',
            fontSize: 11, fontWeight: 600, letterSpacing: '.06em',
            color: '#E8123C', margin: '0 0 10px',
          }}>
            COMMUNITY · 직접 쓰는 노하우
          </p>
          <h1 style={{ fontSize: 32, fontWeight: 800, color: '#fff', letterSpacing: '-.03em', margin: 0 }}>
            커뮤니티
          </h1>
        </div>
        <button
          className="btn"
          onClick={() => alert('로그인 후 이용 가능합니다.')}
          style={{
            background: '#E8123C', color: '#fff',
            fontSize: 14, fontWeight: 700,
            padding: '10px 18px', borderRadius: 10,
            flexShrink: 0, marginTop: 24,
          }}
        >
          ✎ 글쓰기
        </button>
      </div>
      <p style={{ fontSize: 15, color: '#9a9aa4', margin: '0 0 28px' }}>
        팁·기술자료·삽질 후기까지. 현직자들이 직접 등록하고 댓글로 나눕니다.
      </p>

      {/* Post list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {POSTS.map((post, i) => (
          <PostCard
            key={post.id}
            post={post}
            index={i}
            onClick={() => navigate(`/community/${post.id}`)}
          />
        ))}
      </div>
    </main>
  )
}
