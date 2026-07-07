import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import ArticleCard from '../components/ArticleCard'
import ClassCard from '../components/ClassCard'
import EventCard from '../components/EventCard'
import PostCard from '../components/PostCard'
import Skeleton from '../components/Skeleton'
import { fetchHome } from '../api/client'
import { CLASSES, POSTS, EVENTS } from '../data'
import { clickableProps } from '../utils/a11y'

const HOT_CLASS_IDS = ['c4', 'c1', 'c2', 'c6']

function HeroCard({ title, tag, meta, onClick }) {
  return (
    <div
      onClick={onClick}
      className="lk"
      {...clickableProps(onClick)}
      style={{
        background: 'rgba(12,12,15,.5)',
        backdropFilter: 'blur(8px)',
        border: '1px solid rgba(255,255,255,.10)',
        borderRadius: 14,
        padding: '14px 16px',
        cursor: 'pointer',
      }}
    >
      <span style={{
        fontFamily: '"JetBrains Mono", monospace',
        fontSize: 10.5, fontWeight: 600, color: '#E8123C',
        letterSpacing: '.04em', display: 'block', marginBottom: 6,
      }}>
        {tag}
      </span>
      <p style={{ fontSize: 14, fontWeight: 700, color: '#ECECEF', margin: '0 0 8px', lineHeight: 1.4 }}>
        {title}
      </p>
      <p style={{ fontSize: 12.5, color: '#7a7a84', margin: 0 }}>{meta}</p>
    </div>
  )
}

function SectionHeader({ emoji, title, moreLabel, moreTo }) {
  return (
    <div className="sec-header">
      <h2 className="sec-h2">{emoji} {title}</h2>
      <Link to={moreTo} style={{ fontSize: 13.5, color: '#9a9aa4', textDecoration: 'none' }} className="lk">
        {moreLabel || '더보기'} →
      </Link>
    </div>
  )
}

export default function Home() {
  const navigate = useNavigate()
  const [homeData, setHomeData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const hotClasses = HOT_CLASS_IDS
    .map(id => CLASSES.find(c => c.id === id))
    .filter(Boolean)
  const homePosts = POSTS.slice(0, 4)
  const homeEvents = EVENTS.slice(0, 3)

  useEffect(() => {
    fetchHome()
      .then(data => { setHomeData(data); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [])

  const curationSection = homeData?.sections?.find(s => s.category?.slug === 'curation')
  const homeArticles = curationSection?.articles?.slice(0, 3) || []

  return (
    <main>
      {/* Hero */}
      <section style={{
        padding: '64px 40px 70px',
        background: 'radial-gradient(130% 150% at 82% -10%, #FF1E4E 0%, #C00E30 32%, #5A0819 60%, #100A0D 92%)',
        overflow: 'hidden',
      }}>
        <div className="herowrap" style={{
          maxWidth: 1180, margin: '0 auto',
          display: 'flex', gap: 40, alignItems: 'flex-start', position: 'relative',
        }}>
          {/* Left */}
          <div style={{ maxWidth: 580, flex: 1 }}>
            <div style={{
              display: 'inline-flex', alignItems: 'center',
              padding: '5px 14px', borderRadius: 20,
              background: 'rgba(255,255,255,.16)',
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: 11, fontWeight: 600, letterSpacing: '.06em',
              color: '#fff', marginBottom: 22,
            }}>
              AFTER WORK, LEVEL UP
            </div>
            <h1 className="hero-h1" style={{
              fontSize: 52, fontWeight: 800, lineHeight: 1.1,
              letterSpacing: '-.04em', color: '#fff', margin: '0 0 20px',
            }}>
              퇴근 후 30분,<br />금융 AI 한 스푼.
            </h1>
            <p style={{
              fontSize: 16.5, fontWeight: 400, lineHeight: 1.6,
              color: 'rgba(255,255,255,.88)', margin: '0 0 28px', maxWidth: 480,
            }}>
              BC카드 실거래 데이터로 배우고, 현직자와 토론하고, 사내 프로젝트로 연결돼요. 직장인과 개발자를 위한 가장 실무적인 금융 AI 학습 채널.
            </p>
            <div style={{ display: 'flex', gap: 12, marginBottom: 36, flexWrap: 'wrap' }}>
              <button
                className="btn"
                onClick={() => navigate('/onboarding')}
                style={{
                  background: '#fff', color: '#E8123C',
                  fontSize: 15, fontWeight: 700,
                  padding: '13px 26px', borderRadius: 30,
                }}
              >
                무료로 시작하기
              </button>
              <button
                className="btn ghost"
                onClick={() => navigate('/classes')}
                style={{
                  background: 'transparent', color: '#fff',
                  fontSize: 15, fontWeight: 600,
                  padding: '12px 24px', borderRadius: 30,
                  border: '1.5px solid rgba(255,255,255,.4)',
                }}
              >
                클래스 둘러보기
              </button>
            </div>
            {/* Stats */}
            <div style={{ display: 'flex', gap: 26, flexWrap: 'wrap' }}>
              {[
                { num: '38만 건', label: '실습용 익명 거래 데이터' },
                { num: '120+', label: '금융·AI 실무 클래스' },
                { num: '9,400+', label: '수강생·현직자 커뮤니티' },
              ].map(s => (
                <div key={s.num}>
                  <div style={{ fontSize: 21, fontWeight: 800, color: '#fff', marginBottom: 3 }}>{s.num}</div>
                  <div style={{ fontSize: 12, color: 'rgba(255,255,255,.65)' }}>{s.label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Right — floating hero cards */}
          <div className="herocards" style={{
            position: 'absolute', right: 0, top: 0,
            width: 300, display: 'flex', flexDirection: 'column', gap: 12,
          }}>
            <HeroCard
              tag="LIVE 커뮤니티"
              title="사내에서 RAG 도입한 후기 (삽질 포함)"
              meta="지금 23명 보는 중"
              onClick={() => navigate('/community')}
            />
            <HeroCard
              tag="인기 클래스"
              title="이상거래 탐지(FDS) 모델 만들기"
              meta="수강생 1,580명 · 4.9★"
              onClick={() => navigate('/classes')}
            />
          </div>
        </div>
      </section>

      {/* Sections */}
      <div style={{ padding: '40px 40px 8px' }}>
        <div style={{ maxWidth: 1180, margin: '0 auto' }}>

          {/* 1. Curation */}
          <section style={{ marginBottom: 56 }}>
            <SectionHeader emoji="✦" title="나를 위한 큐레이션" moreLabel="큐레이션 더보기" moreTo="/curation" />
            {loading ? (
              <div className="rgrid-3"><Skeleton count={3} variant="article-grid" /></div>
            ) : error ? (
              <p style={{ color: '#9a9aa4', fontSize: 14 }}>콘텐츠를 불러오지 못했습니다. — {error}</p>
            ) : homeArticles.length === 0 ? (
              <p style={{ color: '#9a9aa4', fontSize: 14 }}>아직 글이 없어요.</p>
            ) : (
              <div className="rgrid-3">
                {homeArticles.map((a, i) => (
                  <ArticleCard key={a.id} article={a} index={i} variant="grid" />
                ))}
              </div>
            )}
          </section>

          {/* 2. Hot Classes */}
          <section style={{ marginBottom: 56 }}>
            <SectionHeader emoji="🔥" title="지금 뜨는 클래스" moreTo="/classes" />
            <div className="rgrid-4">
              {hotClasses.map((cls, i) => <ClassCard key={cls.id} cls={cls} index={i} compact />)}
            </div>
          </section>

          {/* 3. Community */}
          <section style={{ marginBottom: 56 }}>
            <SectionHeader emoji="💬" title="이번 주 커뮤니티" moreTo="/community" />
            <div className="rgrid-2">
              {homePosts.map((post, i) => (
                <PostCard
                  key={post.id}
                  post={post}
                  index={i}
                  onClick={() => navigate(`/community/${post.id}`)}
                  compact
                />
              ))}
            </div>
          </section>

          {/* 4. Meet */}
          <section style={{ marginBottom: 24 }}>
            <SectionHeader emoji="📍" title="가야할 밋플" moreTo="/meet" />
            <div className="rgrid-3">
              {homeEvents.map((event, i) => <EventCard key={event.id} event={event} index={i} compact />)}
            </div>
          </section>
        </div>
      </div>
    </main>
  )
}
