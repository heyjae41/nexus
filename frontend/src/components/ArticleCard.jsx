import { Link } from 'react-router-dom'
import { articleGrad } from '../utils/grads'
import { ThumbImage } from './cardKit'
import { clamp2 } from '../utils/cardStyles'

/* Badge Korean labels — §API integration */
const BADGE_LABELS = {
  newsletter: '뉴스레터',
  column: '컬럼',
  guide: '가이드',
  // Legacy rows used the collection site as articleType. Treat them as columns;
  // source/external-link behavior remains controlled separately by isExternal.
  brunch: '컬럼',
}

function badgeLabel(articleType) {
  return BADGE_LABELS[articleType] || articleType || ''
}

/* Grid card — used in home curation section and dashboard */
function GridCard({ article, index }) {
  const grad = articleGrad(index)
  const badge = badgeLabel(article.articleType)

  return (
    <div style={{
      background: '#15151A',
      border: '1px solid rgba(255,255,255,.06)',
      borderRadius: 16,
      overflow: 'hidden',
    }}>
      {/* Thumbnail */}
      <div style={{ height: 124, background: grad, position: 'relative', overflow: 'hidden' }}>
        <ThumbImage src={article.thumbnailUrl} />
        {badge && (
          <span style={{
            position: 'absolute', top: 10, left: 12,
            fontFamily: '"JetBrains Mono", monospace',
            fontSize: 10.5, fontWeight: 600, letterSpacing: '.04em',
            color: '#E8123C',
            background: 'rgba(8,8,11,.7)',
            padding: '3px 8px', borderRadius: 5,
          }}>
            {badge}
          </span>
        )}
      </div>
      {/* Content */}
      <div style={{ padding: '14px 16px 16px' }}>
        <p style={{
          fontSize: 15.5, fontWeight: 700, color: '#ECECEF',
          lineHeight: 1.4, letterSpacing: '-.01em',
          margin: '0 0 10px', ...clamp2,
        }}>
          {article.title || article.summary}
        </p>
        <p style={{ fontSize: 12.5, color: '#7a7a84', margin: 0 }}>
          {article.authorName || article.source} · {article.readMinutes ? `${article.readMinutes}분` : article.readTime}
        </p>
      </div>
    </div>
  )
}

/* Horizontal list card — used in curation list */
function ListCard({ article, index }) {
  const grad = articleGrad(index)
  const badge = badgeLabel(article.articleType)

  return (
    <div style={{
      display: 'flex', gap: 20,
      background: '#15151A',
      border: '1px solid rgba(255,255,255,.06)',
      borderRadius: 16,
      overflow: 'hidden',
      padding: 0,
    }}>
      {/* Thumbnail — hidden on mobile */}
      <div
        className="hidemob"
        style={{ width: 200, flexShrink: 0, background: grad, minHeight: 120, position: 'relative', overflow: 'hidden' }}
      >
        <ThumbImage src={article.thumbnailUrl} />
      </div>
      {/* Content */}
      <div style={{ padding: '18px 20px 18px 0', flex: 1, minWidth: 0 }}>
        {badge && (
          <p style={{
            fontFamily: '"JetBrains Mono", monospace',
            fontSize: 11, fontWeight: 600, letterSpacing: '.04em',
            color: '#E8123C', margin: '0 0 8px',
          }}>
            {badge}
          </p>
        )}
        <p style={{
          fontSize: 19, fontWeight: 700, color: '#ECECEF',
          lineHeight: 1.4, letterSpacing: '-.015em',
          margin: '0 0 8px',
        }}>
          {article.title}
        </p>
        {(article.summary || article.excerpt) && (
          <p style={{ fontSize: 14, color: '#9a9aa4', margin: '0 0 12px', ...clamp2 }}>
            {article.summary || article.excerpt}
          </p>
        )}
        <p style={{ fontSize: 13, color: '#7a7a84', margin: 0 }}>
          {article.authorName || article.source} · {article.readMinutes ? `${article.readMinutes}분 읽기` : `${article.readTime} 읽기`}
        </p>
      </div>
    </div>
  )
}

/**
 * ArticleCard — CRITICAL LINK RULE:
 * if isExternal === true → <a href={linkUrl} target="_blank">
 * otherwise → <Link to={/articles/:id}>
 */
export default function ArticleCard({ article, index = 0, variant = 'grid' }) {
  const inner = variant === 'list'
    ? <ListCard article={article} index={index} />
    : <GridCard article={article} index={index} />

  if (article.isExternal && article.linkUrl) {
    return (
      <a
        href={article.linkUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="card"
        style={{ display: 'block', textDecoration: 'none', color: 'inherit' }}
        data-testid="article-card-external"
      >
        {inner}
      </a>
    )
  }

  return (
    <Link
      to={`/articles/${article.id}`}
      className="card"
      style={{ display: 'block', textDecoration: 'none', color: 'inherit' }}
      data-testid="article-card-internal"
    >
      {inner}
    </Link>
  )
}
