import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { fetchArticle, fetchArticles, likeArticle } from '../api/client'
import { EDITORIAL_ARTICLES } from '../data'
import { fmtEn, articleGrad } from '../utils/grads'
import KeyVisual from '../components/KeyVisual'
import '../styles/article.css'

/* ---- Reading progress bar ---- */
function useReadingProgress() {
  useEffect(() => {
    const update = () => {
      const el = document.getElementById('readprog')
      if (!el) return
      const h = document.documentElement
      const max = (h.scrollHeight - h.clientHeight) || 1
      el.style.width = Math.min(100, Math.max(0, (h.scrollTop / max) * 100)) + '%'
    }
    window.addEventListener('scroll', update, { passive: true })
    update()
    return () => window.removeEventListener('scroll', update)
  }, [])
}

/* ---- Animated hero ---- */
function AnimatedHero({ article, heroMotion = true }) {
  const theme = article?.theme
  const play = heroMotion ? 'running' : 'paused'
  const heroBase = theme?.heroBase || 'radial-gradient(120% 130% at 15% 8%, #3A0A18 0%, #1A0509 50%, #08080B 100%)'
  const chipBg = theme?.chipBg || 'rgba(232,18,60,.18)'
  const chipCol = theme?.chipCol || '#F4788F'

  return (
    <div className="heroart" style={{ background: heroBase }}>
      <div className="heroart-blobA heroart-blob"
        style={{ background: theme?.blobA || 'radial-gradient(circle,rgba(232,18,60,.8),transparent 68%)',
          animationName: 'drifta', animationDuration: '17s', animationTimingFunction: 'ease-in-out',
          animationIterationCount: 'infinite', animationPlayState: play }} />
      <div className="heroart-blobB heroart-blob"
        style={{ background: theme?.blobB || 'radial-gradient(circle,rgba(232,18,60,.5),transparent 66%)',
          animationName: 'driftb', animationDuration: '21s', animationTimingFunction: 'ease-in-out',
          animationIterationCount: 'infinite', animationPlayState: play }} />
      <div className="heroart-blobC heroart-blob"
        style={{ background: theme?.blobC || 'radial-gradient(circle,rgba(232,18,60,.4),transparent 70%)',
          animationName: 'driftc', animationDuration: '15s', animationTimingFunction: 'ease-in-out',
          animationIterationCount: 'infinite', animationPlayState: play }} />
      <div className="heroart-ring"
        style={{ background: theme?.ring || 'conic-gradient(from 0deg, #E8123C, #7A0A22, #E8123C)',
          animationName: 'spin', animationDuration: '26s', animationTimingFunction: 'linear',
          animationIterationCount: 'infinite', animationPlayState: play }} />
      <div className="heroart-grid"
        style={{ background: 'radial-gradient(rgba(255,255,255,.14) 1px, transparent 1px)',
          backgroundSize: '28px 28px',
          animationName: 'gridpan', animationDuration: '12s', animationTimingFunction: 'linear',
          animationIterationCount: 'infinite', animationPlayState: play }} />
      <div className="heroart-fade" />
      <div className="heroinner pad maxw-1180">
        <div className="herochip" style={{ background: chipBg, color: chipCol }}>
          {article?.koType ? `${article.koType} · ${article.section || theme?.name || ''}` : 'EDU.AI'}
        </div>
        <h1 className="herotitle">{article?.title || ''}</h1>
        {article?.subtitle && <p className="herosub">{article.subtitle}</p>}
      </div>
    </div>
  )
}

/* ---- Body block renderer ---- */
function BodyBlock({ block }) {
  const { t, x, items, label } = block
  if (t === 'p') return <p className="art-p">{x}</p>
  if (t === 'h2') return (
    <h2 className="art-h2"><div className="art-h2-bar" />{x}</h2>
  )
  if (t === 'q') return <blockquote className="art-quote">"{x}"</blockquote>
  if (t === 'ul') return (
    <ul className="art-ul">
      {(items || []).map((item, i) => (
        <li key={i}><div className="art-ul-bullet" />{item}</li>
      ))}
    </ul>
  )
  if (t === 'call') return (
    <div className="art-callout">
      <p className="art-callout-label">{label}</p>
      <p className="art-callout-body">{x}</p>
    </div>
  )
  if (t === 'def') return (
    <div className="art-def">
      <p className="art-def-label">한 줄 정의</p>
      <p className="art-def-text">{x}</p>
    </div>
  )
  return null
}

/* ---- Related article card ---- */
function RelatedCard({ art, onNavigate }) {
  const theme = art.theme
  return (
    <div
      className="card"
      onClick={onNavigate}
      style={{
        display: 'flex', gap: 16, alignItems: 'flex-start',
        background: '#15151A', border: '1px solid rgba(255,255,255,.06)',
        borderRadius: 16, padding: '16px', cursor: 'pointer',
      }}
    >
      <div style={{
        width: 120, height: 80, borderRadius: 10, flexShrink: 0,
        background: theme?.relGrad || articleGrad(0),
        backgroundImage: `radial-gradient(rgba(255,255,255,.07) 1px, transparent 1px)`,
        backgroundSize: '14px 14px',
      }} />
      <div>
        <p style={{
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: 10.5, fontWeight: 600, color: theme?.relCol || '#F4788F',
          letterSpacing: '.04em', margin: '0 0 6px',
        }}>
          {art.koType}
        </p>
        <p style={{ fontSize: 16, fontWeight: 700, color: '#ECECEF', lineHeight: 1.4, margin: '0 0 6px' }}>
          {art.title}
        </p>
        <p style={{ fontSize: 12.5, color: '#7a7a84', margin: 0 }}>
          {art.author?.name || art.authorName} · {art.readTime}
        </p>
      </div>
    </div>
  )
}

/* ---- Main view ---- */
export default function ArticleDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [apiArticle, setApiArticle] = useState(null)
  const [relatedFromApi, setRelatedFromApi] = useState([])
  const [apiLoading, setApiLoading] = useState(true)
  const [loadError, setLoadError] = useState(false)
  const loadSeq = useRef(0) // id 연속 전환 시 늦게 도착한 이전 응답(stale)을 무시
  const [liked, setLiked] = useState(false)
  const [saved, setSaved] = useState(false)
  const [likeCount, setLikeCount] = useState(0)
  const likeInFlight = useRef(false)
  const hasCounted = useRef(false) // 이 글에 이미 +1 을 보냈는지 (증가 전용 API 어뷰징 방지)

  useReadingProgress()

  const staticArt = EDITORIAL_ARTICLES.find(a => a.id === id)

  const loadArticle = useCallback(async () => {
    const seq = ++loadSeq.current
    setApiLoading(true)
    setLoadError(false)
    try {
      const [artData, listData] = await Promise.all([
        fetchArticle(id),
        fetchArticles({ category: 'curation', page: 1, size: 20 }).catch(() => ({ data: [], articles: [] })),
      ])
      if (seq !== loadSeq.current) return // 이미 다른 글로 이동함 — stale 응답 폐기
      setApiArticle(artData)
      setLikeCount(artData.likesCount ?? (staticArt?.rawLikes || 0))
      const items = listData.data ?? listData.articles ?? []
      // API 의 id 는 숫자, useParams 의 id 는 문자열 — 타입 정규화 후 자기 자신 제외
      setRelatedFromApi(items.filter(a => String(a.id) !== String(id)).slice(0, 2))
    } catch {
      if (seq !== loadSeq.current) return
      setLoadError(true)
      setLikeCount(staticArt?.rawLikes || 0)
    } finally {
      if (seq === loadSeq.current) setApiLoading(false)
    }
  }, [id, staticArt?.rawLikes])

  useEffect(() => {
    setLiked(false)
    setSaved(false)
    hasCounted.current = false
    loadArticle()
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [id, loadArticle])

  const article = { ...staticArt, ...apiArticle }
  const displayLikeCount = fmtEn(likeCount)

  const handleLike = async () => {
    if (likeInFlight.current) return
    if (liked) {
      // 취소 — 백엔드는 증가 전용(감소 API 없음)이므로 로컬 표시만 되돌린다
      setLiked(false)
      setLikeCount(c => Math.max(0, c - 1))
      return
    }
    setLiked(true)
    setLikeCount(c => c + 1) // 옵티미스틱 +1 (서버 확정값으로 곧 대체)
    if (hasCounted.current) return // 재좋아요 — 서버 카운트 중복 증가 방지 (세션당 1회)
    likeInFlight.current = true
    try {
      const data = await likeArticle(id)
      hasCounted.current = true
      if (data?.likesCount !== undefined) setLikeCount(data.likesCount)
    } catch {
      setLiked(false)
      setLikeCount(c => Math.max(0, c - 1))
    } finally {
      likeInFlight.current = false
    }
  }

  const btnStyle = (active) => ({
    display: 'flex', alignItems: 'center', gap: 7,
    padding: '9px 18px', borderRadius: 24, fontSize: 14, fontWeight: 600,
    border: `1px solid ${active ? 'rgba(232,18,60,.5)' : 'rgba(255,255,255,.1)'}`,
    background: active ? 'rgba(232,18,60,.16)' : 'rgba(255,255,255,.05)',
    color: active ? '#F4788F' : '#c9c9d2',
    cursor: 'pointer', transition: 'all .15s',
  })

  // API 실패 + 정적 폴백도 없으면 빈 화면 대신 명확한 에러 안내 (다른 뷰와 동일한 UX)
  if (loadError && !staticArt && !apiArticle) {
    return (
      <main style={{ padding: '80px 20px', maxWidth: 480, margin: '0 auto', textAlign: 'center' }}>
        <p style={{ fontSize: 16, color: '#9a9aa4', marginBottom: 24 }}>글을 불러오지 못했습니다.</p>
        <button
          className="btn"
          onClick={loadArticle}
          style={{
            background: '#E8123C', color: '#fff',
            padding: '10px 20px', borderRadius: 10, fontSize: 14, fontWeight: 700,
          }}
        >
          다시 시도
        </button>
      </main>
    )
  }

  const readW = 720
  const related = relatedFromApi.length > 0
    ? relatedFromApi
    : EDITORIAL_ARTICLES.filter(a => a.id !== id).slice(0, 2)

  return (
    <>
      {/* Reading progress */}
      <div className="readprog-track">
        <div id="readprog" />
      </div>

      {/* Animated hero */}
      <AnimatedHero article={article} />

      {/* Meta bar */}
      {!apiLoading && article?.author && (
        <div style={{ maxWidth: readW, margin: '24px auto 0', padding: '0 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap', paddingBottom: 18, borderBottom: '1px solid rgba(255,255,255,.08)' }}>
            <div style={{
              width: 34, height: 34, borderRadius: '50%', flexShrink: 0,
              background: article.author.avatarBg || 'linear-gradient(135deg,#E8123C,#7A0A22)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14, fontWeight: 700, color: '#fff',
            }}>
              {article.author.initial}
            </div>
            <div>
              <span style={{ fontSize: 14, fontWeight: 700, color: '#ECECEF' }}>{article.author.name}</span>
              {article.author.role && <span style={{ fontSize: 12.5, color: '#8a8a94', marginLeft: 8 }}>{article.author.role}</span>}
            </div>
            <div style={{ marginLeft: 'auto', fontFamily: '"JetBrains Mono", monospace', fontSize: 12.5, color: '#6a6a74' }}>
              {article.date} · {article.readTime}
              {article.rawViews && <span style={{ marginLeft: 10 }}>조회 {fmtEn(article.rawViews)} · 좋아요 {displayLikeCount}</span>}
            </div>
          </div>
        </div>
      )}

      {/* Action row */}
      <div style={{ maxWidth: readW, margin: '16px auto', padding: '0 20px', display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <button className="btn actn" onClick={handleLike} style={btnStyle(liked)}>♥ 좋아요 {displayLikeCount}</button>
        <button className="btn actn" onClick={() => setSaved(s => !s)} style={btnStyle(saved)}>🔖 {saved ? '저장됨' : '저장'}</button>
        <div style={{ flex: 1 }} />
        <button className="btn actn" style={btnStyle(false)}>↗ 공유</button>
      </div>

      {/* Key visual — skip for external (brunch) articles */}
      {!article?.isExternal && (staticArt || article?.keyVisualHtml) && (
        <div style={{ maxWidth: readW, margin: '24px auto', padding: '0 20px' }}>
          <KeyVisual
            articleId={id}
            keyVisualHtml={article?.keyVisualHtml}
            figCaption={staticArt?.figCaption}
          />
        </div>
      )}

      {/* Body — external articles show a notice card linking to the original */}
      {article?.isExternal ? (
        <div className="art-body" style={{ padding: '0 20px', margin: '32px auto' }}>
          <div style={{
            background: '#15151A', border: '1px solid rgba(255,255,255,.08)',
            borderRadius: 16, padding: '32px 24px', textAlign: 'center',
          }}>
            <p style={{ fontSize: 16, color: '#9a9aa4', marginBottom: 20 }}>
              이 글은 브런치에서 볼 수 있습니다
            </p>
            <a
              href={article.linkUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                background: '#E8123C', color: '#fff',
                padding: '11px 24px', borderRadius: 24,
                fontSize: 14, fontWeight: 700, textDecoration: 'none',
              }}
            >
              원문 보기 →
            </a>
          </div>
        </div>
      ) : (
        <div className="art-body" style={{ padding: '0 20px', margin: '32px auto' }}>
          {article?.bodyHtml ? (
            <div dangerouslySetInnerHTML={{ __html: article.bodyHtml }} />
          ) : staticArt?.blocks ? (
            staticArt.blocks.map((block, i) => <BodyBlock key={i} block={block} />)
          ) : apiLoading ? (
            <p style={{ color: '#7a7a84' }}>본문을 불러오는 중...</p>
          ) : null}
        </div>
      )}

      {/* Sources & disclaimer */}
      {staticArt?.sources?.length > 0 && (
        <div style={{ maxWidth: readW, margin: '0 auto 12px', padding: '0 20px' }}>
          <p style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11.5, color: '#6a6a74', marginBottom: 8, letterSpacing: '.04em' }}>참고한 원 보도</p>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {staticArt.sources.map((s, i) => (
              <li key={i} style={{ fontSize: 13.5, color: '#9a9aa4', marginBottom: 4 }}>— {s}</li>
            ))}
          </ul>
        </div>
      )}
      {staticArt?.disclaimer && (
        <p style={{ maxWidth: readW, margin: '0 auto 24px', padding: '0 20px', fontSize: 12, fontStyle: 'italic', color: '#6a6a74' }}>
          {staticArt.disclaimer}
        </p>
      )}

      {/* Tags */}
      {(staticArt?.tags || article?.tags)?.length > 0 && (
        <div style={{ maxWidth: readW, margin: '0 auto 24px', padding: '0 20px', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {(staticArt?.tags || article?.tags).map(tag => (
            <span key={tag} className="tagchip" style={{
              padding: '5px 12px', borderRadius: 20,
              background: 'rgba(232,18,60,.08)', border: '1px solid rgba(232,18,60,.2)',
              fontSize: 13, color: '#9a9aa4', cursor: 'pointer', transition: 'all .15s',
            }}>
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Author card */}
      {article?.author && (
        <div style={{ maxWidth: readW, margin: '0 auto 48px', padding: '0 20px' }}>
          <div style={{
            background: '#131318', border: '1px solid rgba(255,255,255,.07)',
            borderRadius: 18, padding: '20px 22px',
            display: 'flex', gap: 16, alignItems: 'flex-start',
          }}>
            <div style={{
              width: 54, height: 54, borderRadius: '50%', flexShrink: 0,
              background: article.author.avatarBg || 'linear-gradient(135deg,#E8123C,#7A0A22)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 20, fontWeight: 800, color: '#fff',
            }}>
              {article.author.initial}
            </div>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: 15.5, fontWeight: 800, color: '#fff', margin: '0 0 4px' }}>{article.author.name}</p>
              <p style={{ fontSize: 13.5, color: '#9a9aa4', margin: '0 0 10px' }}>{article.author.bio}</p>
              <button className="btn" style={{
                background: '#E8123C', color: '#fff',
                fontSize: 13, fontWeight: 700, padding: '6px 16px', borderRadius: 20,
              }}>구독</button>
            </div>
          </div>
        </div>
      )}

      {/* Related articles */}
      {related.length > 0 && (
        <div style={{ maxWidth: 1180, margin: '0 auto 80px', padding: '0 20px' }}>
          <h2 style={{ fontSize: 20, fontWeight: 800, color: '#fff', margin: '0 0 20px' }}>함께 읽으면 좋은 글</h2>
          <div className="rgrid-2">
            {related.map(art => (
              <RelatedCard
                key={art.id}
                art={{ ...EDITORIAL_ARTICLES.find(a => a.id === art.id), ...art }}
                onNavigate={() => navigate(`/articles/${art.id}`)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Floating type switcher */}
      <div className="switcher">
        <span className="swlabel">유형</span>
        {EDITORIAL_ARTICLES.map(a => (
          <Link
            key={a.id}
            to={`/articles/${a.id}`}
            className="sw-btn"
            style={{
              background: id === a.id ? '#E8123C' : 'transparent',
              color: id === a.id ? '#fff' : '#b6b6c0',
              textDecoration: 'none',
            }}
          >
            {a.koType}
          </Link>
        ))}
      </div>
    </>
  )
}
