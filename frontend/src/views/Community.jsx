import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { PostCardList } from '../components/PostCard'
import Skeleton from '../components/Skeleton'
import PageLabel from '../components/PageLabel'
import FilterChips from '../components/FilterChips'
import { usePagedList } from '../hooks/usePagedList'
import { fetchPosts } from '../api/client'

const PAGE_SIZE = 20
const BADGE_FILTERS = [
  { value: null, label: '전체' },
  { value: '자료', label: '자료' },
  { value: '노하우', label: '노하우' },
  { value: '팁', label: '팁' },
  { value: '기술자료', label: '기술자료' },
]

export default function Community({ user }) {
  const navigate = useNavigate()
  const [tag, setTag] = useState(null)

  const fetchPage = useCallback(
    (p, selectedTag = tag) => fetchPosts({ tag: selectedTag, page: p, size: PAGE_SIZE }),
    [tag],
  )

  const { items: posts, loading, error } = usePagedList(fetchPage)

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
          <PageLabel>COMMUNITY · 직접 쓰는 노하우</PageLabel>
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
      <p style={{ fontSize: 15, color: '#9a9aa4', margin: '0 0 18px' }}>
        팁·기술자료·삽질 후기까지. 현직자들이 직접 등록하고 댓글로 나눕니다.
      </p>

      <FilterChips
        options={BADGE_FILTERS}
        value={tag}
        onChange={setTag}
        ariaLabel="커뮤니티 배지 필터"
      />

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
          <PostCardList posts={posts} />
        </div>
      )}
    </main>
  )
}
