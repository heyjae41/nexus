import { Link } from 'react-router-dom'

const FOOTER_LINKS = [
  { label: '클래스', to: '/classes' },
  { label: '큐레이션', to: '/curation' },
  { label: '커뮤니티', to: '/community' },
  { label: 'meet.pl', to: '/meet' },
  { label: 'AI핫딜', to: '/hotdeal' },
  { label: 'eat.pl', href: 'https://web.paybooc.ai/place/what-to-eat' },
]

export default function Footer() {
  return (
    <footer style={{
      background: '#0C0C10',
      borderTop: '1px solid rgba(255,255,255,.06)',
      padding: '48px 40px',
      marginTop: 64,
      textAlign: 'center',
    }}>
      <div style={{ maxWidth: 1180, margin: '0 auto' }}>
        <p style={{ fontSize: 18, fontWeight: 800, color: '#fff', margin: '0 0 10px', letterSpacing: '-.02em' }}>
          금융과 AI, 일하면서 배웁니다.
        </p>
        <p style={{ fontSize: 13, color: '#6a6a74', margin: '0 0 24px' }}>
          BC카드 AI 사업팀 · NEXUS — credit + finance
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: 24, flexWrap: 'wrap' }}>
          {FOOTER_LINKS.map(link =>
            link.href ? (
              <a
                key={link.label}
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                style={{ fontSize: 13.5, color: '#6a6a74', textDecoration: 'none', transition: 'color .15s' }}
                className="lk"
              >
                {link.label} ↗
              </a>
            ) : (
              <Link
                key={link.label}
                to={link.to}
                style={{ fontSize: 13.5, color: '#6a6a74', textDecoration: 'none', transition: 'color .15s' }}
                className="lk"
              >
                {link.label}
              </Link>
            )
          )}
        </div>
      </div>
    </footer>
  )
}
