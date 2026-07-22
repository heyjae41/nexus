import { useNavigate } from 'react-router-dom'
import { communityAvatarGrad, fmtKo, initial } from '../utils/grads'
import { clickableProps } from '../utils/a11y'
import { timeAgo } from '../utils/timeAgo'

/* API 응답 글(post)을 PostCard 가 기대하는 카드 셰이프로 변환한다 */
function toPostCardShape(post) {
  return {
    id: post.id,
    tag: post.tag,
    title: post.title,
    author: post.authorName,
    time: timeAgo(post.createdAt),
    likes: post.likesCount,
    commentCount: post.commentsCount,
  }
}

/** API 글 목록을 카드 목록으로 렌더 — 클릭 시 상세로 이동 (홈·커뮤니티 공용). */
export function PostCardList({ posts, compact = false }) {
  const navigate = useNavigate()
  return posts.map((post, i) => (
    <PostCard
      key={post.id}
      post={toPostCardShape(post)}
      index={i}
      compact={compact}
      onClick={() => navigate(`/community/${post.id}`)}
    />
  ))
}

/**
 * Shared PostCard — community post listing card.
 * compact=true  → Home page style (50px avatar, clamped title, simple meta)
 * compact=false → Community page style (46px avatar, tag chip, author+time, full meta)
 */
export default function PostCard({ post, index, onClick, compact = false }) {
  const grad = communityAvatarGrad(index)

  return (
    <div
      className="card"
      onClick={onClick}
      {...clickableProps(onClick, 'link')}
      style={{
        display: 'flex', gap: 14, alignItems: 'flex-start',
        background: '#15151A', border: '1px solid rgba(255,255,255,.06)',
        borderRadius: 14, padding: compact ? '14px 16px' : '16px 18px',
      }}
    >
      <div style={{
        width: compact ? 50 : 46,
        height: compact ? 50 : 46,
        borderRadius: '50%',
        background: grad, flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: compact ? 18 : 17, fontWeight: 800, color: '#fff',
      }}>
        {initial(post.author)}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        {!compact && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
            <span className="tagchip" style={{
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: 10.5, fontWeight: 600, letterSpacing: '.03em',
              color: '#E8123C', background: 'rgba(232,18,60,.12)',
              border: '1px solid rgba(232,18,60,.2)',
              padding: '2px 8px', borderRadius: 5, transition: 'all .15s',
            }}>
              {post.tag}
            </span>
            <span style={{ fontSize: 12.5, color: '#7a7a84' }}>
              {post.author} · {post.time}
            </span>
          </div>
        )}
        <p style={{
          fontSize: compact ? 15.5 : 17, fontWeight: 700, color: '#ECECEF',
          lineHeight: 1.4, margin: '0 0 8px',
          ...(compact ? {
            display: '-webkit-box', WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical', overflow: 'hidden',
          } : {}),
        }}>
          {post.title}
        </p>
        <p style={{ fontSize: 12.5, color: '#7a7a84', margin: 0 }}>
          {compact
            ? `#${post.tag} · 좋아요 ${fmtKo(post.likes)} · 댓글 ${post.commentCount}`
            : `♥ ${fmtKo(post.likes)} · 💬 ${post.commentCount}`
          }
        </p>
      </div>
    </div>
  )
}
