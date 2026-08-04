import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import ArticleCard from '../components/ArticleCard'
import ClassCard from '../components/ClassCard'
import EventCard from '../components/EventCard'
import { PostCardList } from '../components/PostCard'
import Skeleton from '../components/Skeleton'
import { fetchClasses, fetchHome, fetchEvents, fetchPosts } from '../api/client'
import { clickableProps } from '../utils/a11y'


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

const HERO_SERVICES = [
  { emoji: '✦', name: '큐레이션', desc: '매일 골라 읽는 AI 글', to: '/curation' },
  { emoji: '▶', name: '클래스', desc: '검증된 명강의 소개', to: '/classes' },
  { emoji: '📍', name: 'meet.pl', desc: '밋업·해커톤 소식', to: '/meet' },
  { emoji: '💬', name: '커뮤니티', desc: '현직자 팁·Q&A', to: '/community' },
  { emoji: '⚡', name: 'AI핫딜', desc: '오늘의 특가 수집', to: '/hotdeal' },
  { emoji: '🍜', name: 'eat.pl', desc: '회사 근처 맛집 검색', href: 'https://web.paybooc.ai/place/eatpl-home' },
  { emoji: '💳', name: 'card.Pick', desc: '카드사 여행혜택 모음', to: '/cardpick' },
]

function ServiceChip({ service }) {
  const style = {
    display: 'inline-flex', alignItems: 'center', gap: 7,
    padding: '8px 14px', borderRadius: 22,
    background: 'rgba(255,255,255,.10)',
    border: '1px solid rgba(255,255,255,.16)',
    backdropFilter: 'blur(6px)',
    textDecoration: 'none', cursor: 'pointer',
    transition: 'background .15s, border-color .15s',
  }
  const inner = (
    <>
      <span aria-hidden="true" style={{ fontSize: 12 }}>{service.emoji}</span>
      <span style={{ fontSize: 13, fontWeight: 700, color: '#fff' }}>{service.name}</span>
      <span style={{ fontSize: 12, color: 'rgba(255,255,255,.68)' }}>{service.desc}</span>
    </>
  )
  return service.href ? (
    <a href={service.href} target="_blank" rel="noopener noreferrer" className="lk" style={style}>{inner}</a>
  ) : (
    <Link to={service.to} className="lk" style={style}>{inner}</Link>
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
  const [homeEvents, setHomeEvents] = useState([])
  const [hotClasses, setHotClasses] = useState([])
  const [classesLoading, setClassesLoading] = useState(true)
  const [homePosts, setHomePosts] = useState([])

  useEffect(() => {
    fetchHome()
      .then(data => { setHomeData(data); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
    fetchEvents({ page: 1, size: 3 })
      .then(json => setHomeEvents(json.data ?? []))
      .catch(() => setHomeEvents([]))
    fetchClasses({ page: 1, size: 4 })
      .then(json => setHotClasses(json.data ?? []))
      .catch(() => setHotClasses([]))
      .finally(() => setClassesLoading(false))
    fetchPosts({ page: 1, size: 4 })
      .then(json => setHomePosts(json.data ?? []))
      .catch(() => setHomePosts([]))
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
              쏟아지는 AI 소식을 다 쫓을 필요는 없어요. 읽을만한 글, 들을만한 강의, 가볼만한 밋업과 오늘의 핫딜까지 — BC카드 AI사업팀이 매일 직접 골라 담아요.
            </p>
            {/* Service chips — 매일 골라 담는 여섯 채널 */}
            <div>
              <div style={{
                fontFamily: '"JetBrains Mono", monospace',
                fontSize: 10.5, fontWeight: 600, letterSpacing: '.08em',
                color: 'rgba(255,255,255,.55)', marginBottom: 10,
              }}>
                WHAT&apos;S INSIDE
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {HERO_SERVICES.map(s => <ServiceChip key={s.name} service={s} />)}
              </div>
            </div>
          </div>

          {/* Right — floating hero cards (실데이터: 최신 큐레이션 글 + 다가오는 밋업) */}
          {(homeArticles.length > 0 || homeEvents.length > 0) && (
            <div className="herocards" style={{
              position: 'absolute', right: 0, top: 0,
              width: 300, display: 'flex', flexDirection: 'column', gap: 12,
            }}>
              {homeArticles.length > 0 && (
                <HeroCard
                  tag="오늘의 큐레이션"
                  title={homeArticles[0].title}
                  meta={`${homeArticles[0].authorName} · ${homeArticles[0].readMinutes}분 읽기`}
                  onClick={() => navigate('/curation')}
                />
              )}
              {homeEvents.length > 0 && (
                <HeroCard
                  tag="다가오는 밋업"
                  title={homeEvents[0].title}
                  meta={homeEvents[0].place || homeEvents[0].area || 'meet.pl에서 확인'}
                  onClick={() => navigate('/meet')}
                />
              )}
            </div>
          )}
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
            {classesLoading ? (
              <div className="rgrid-4"><Skeleton count={4} variant="article-grid" /></div>
            ) : hotClasses.length === 0 ? (
              <p style={{ color: '#9a9aa4', fontSize: 14 }}>수집된 클래스가 아직 없어요.</p>
            ) : (
              <div className="rgrid-4">
                {hotClasses.map((cls, i) => <ClassCard key={cls.id} cls={cls} index={i} compact />)}
              </div>
            )}
          </section>

          {/* 3. Community */}
          <section style={{ marginBottom: 56 }}>
            <SectionHeader emoji="💬" title="이번 주 커뮤니티" moreTo="/community" />
            <div className="rgrid-2">
              <PostCardList posts={homePosts} compact />
            </div>
          </section>

          {/* 4. Meet */}
          {homeEvents.length > 0 && (
            <section style={{ marginBottom: 24 }}>
              <SectionHeader emoji="📍" title="가야할 밋플" moreTo="/meet" />
              <div className="rgrid-3">
                {homeEvents.map((event, i) => (
                  <EventCard key={event.id} event={event} index={i} compact external />
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </main>
  )
}
