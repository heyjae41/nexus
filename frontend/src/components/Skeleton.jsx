/* Loading skeleton components */

function Box({ w = '100%', h = 16, r = 6, style = {} }) {
  return (
    <div
      className="sk"
      style={{ width: w, height: h, borderRadius: r, flexShrink: 0, ...style }}
    />
  )
}

export function ArticleCardSkeleton() {
  return (
    <div style={{
      background: '#15151A',
      border: '1px solid rgba(255,255,255,.06)',
      borderRadius: 16, overflow: 'hidden',
    }}>
      <Box h={124} r={0} />
      <div style={{ padding: '14px 16px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        <Box h={14} w="90%" />
        <Box h={14} w="70%" />
        <Box h={12} w="50%" style={{ marginTop: 4 }} />
      </div>
    </div>
  )
}

export function ArticleListSkeleton() {
  return (
    <div style={{
      display: 'flex', gap: 20,
      background: '#15151A',
      border: '1px solid rgba(255,255,255,.06)',
      borderRadius: 16, overflow: 'hidden',
    }}>
      <Box w={200} h={120} r={0} style={{ flexShrink: 0 }} />
      <div style={{ flex: 1, padding: '18px 20px 18px 0', display: 'flex', flexDirection: 'column', gap: 10 }}>
        <Box h={11} w="30%" />
        <Box h={18} w="85%" />
        <Box h={14} w="65%" />
        <Box h={12} w="40%" />
      </div>
    </div>
  )
}

export function ClassCardSkeleton() {
  return (
    <div style={{
      background: '#15151A',
      border: '1px solid rgba(255,255,255,.06)',
      borderRadius: 16, overflow: 'hidden',
    }}>
      <Box h={148} r={0} />
      <div style={{ padding: '12px 14px 14px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        <Box h={14} w="90%" />
        <Box h={14} w="70%" />
        <Box h={12} w="50%" />
        <Box h={16} w="35%" style={{ marginTop: 4 }} />
      </div>
    </div>
  )
}

export default function Skeleton({ count = 3, variant = 'article-grid' }) {
  const Component = {
    'article-grid': ArticleCardSkeleton,
    'article-list': ArticleListSkeleton,
    'class': ClassCardSkeleton,
  }[variant] || ArticleCardSkeleton

  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <Component key={i} />
      ))}
    </>
  )
}
