import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import PostCard from '../components/PostCard'
import Skeleton from '../components/Skeleton'
import { fetchPosts } from '../api/client'
import { timeAgo } from '../utils/timeAgo'

const PAGE_SIZE = 20

function toCardShape(post, index) {
  return {
    id: post.id,
    tag: post.tag,
    title: post.title,
    author: post.authorName,
    time: timeAgo(post.createdAt),
    likes: post.likesCount,
    commentCount: post.commentsCount,
    _index: index,
  }
}

export default function Community({ user }) {
  const navigate = useNavigate()
  const [posts, setPosts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchPosts({ page: 1, size: PAGE_SIZE })
      .then(json => {
        setPosts(json.data ?? [])
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  const handleWrite = () => {
    if (user) {
      navigate('/community/write')
    } else {
      navigate('/onboarding')
    }
  }

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
          onClick={handleWrite}
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
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Skeleton count={5} variant="post" />
        </div>
      ) : error ? (
        <p style={{ color: '#9a9aa4', fontSize: 14 }}>글을 불러오지 못했습니다. — {error}</p>
      ) : posts.length === 0 ? (
        <p style={{ color: '#9a9aa4', fontSize: 14 }}>아직 글이 없어요.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {posts.map((post, i) => (
            <PostCard
              key={post.id}
              post={toCardShape(post, i)}
              index={i}
              onClick={() => navigate(`/community/${post.id}`)}
            />
          ))}
        </div>
      )}
    </main>
  )
}
