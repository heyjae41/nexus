import { useNavigate, useLocation, Link } from 'react-router-dom'
import { clickableProps } from '../utils/a11y'
import { displayName } from '../utils/user'

const NAV_LINKS = [
  { label: '홈', path: '/', match: ['/'] },
  { label: '큐레이션', path: '/curation', match: ['/curation', '/articles/'] },
  { label: '클래스', path: '/classes', match: ['/classes'] },
  { label: '커뮤니티', path: '/community', match: ['/community'] },
  { label: 'meet.pl', path: '/meet', match: ['/meet'] },
  { label: 'AI핫딜', path: '/hotdeal', match: ['/hotdeal'] },
]

function isActive(pathname, match) {
  if (match[0] === '/') return pathname === '/'
  return match.some(m => pathname.startsWith(m))
}

export default function Nav({ user }) {
  const navigate = useNavigate()
  const { pathname } = useLocation()

  const goOnboarding = () => navigate(user ? '/dashboard' : '/onboarding')

  return (
    <header style={{
      position: 'sticky', top: 0, zIndex: 50,
      background: 'rgba(8,8,11,.82)',
      backdropFilter: 'blur(14px)',
      WebkitBackdropFilter: 'blur(14px)',
      borderBottom: '1px solid rgba(255,255,255,.07)',
      padding: '14px 28px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 0, maxWidth: 1180, margin: '0 auto' }}>
        {/* Logo */}
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 7, textDecoration: 'none', marginRight: 28 }}>
          <div style={{ width: 11, height: 11, borderRadius: '50%', background: '#E8123C', flexShrink: 0 }} />
          <span style={{ fontSize: 21, fontWeight: 800, color: '#fff', letterSpacing: '-.03em' }}>NEXUS</span>
        </Link>

        {/* Nav links */}
        <nav className="topnav-links" style={{ display: 'flex', alignItems: 'center', gap: 22 }}>
          {NAV_LINKS.map(link => (
            <Link
              key={link.path}
              to={link.path}
              style={{
                fontSize: 14.5, fontWeight: 600, letterSpacing: '-.01em',
                color: isActive(pathname, link.match) ? '#E8123C' : '#a6a6b0',
                textDecoration: 'none',
                transition: 'color .15s',
              }}
            >
              {link.label}
            </Link>
          ))}
          <a
            href="https://web.paybooc.ai/place/what-to-eat"
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontSize: 14.5, fontWeight: 600, color: '#a6a6b0', textDecoration: 'none' }}
          >
            eat.pl ↗
          </a>
        </nav>

        <div style={{ flex: 1 }} />

        {/* Search — hidden on mobile */}
        <div
          className="hidemob"
          onClick={() => navigate('/classes')}
          {...clickableProps(() => navigate('/classes'))}
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            width: 210, padding: '8px 14px',
            background: '#141419', borderRadius: 10,
            border: '1px solid rgba(255,255,255,.08)',
            cursor: 'pointer', marginRight: 16,
          }}
        >
          <span style={{ fontSize: 14, color: '#6a6a74' }}>⌕</span>
          <span style={{ fontSize: 13.5, color: '#6a6a74' }}>무엇을 배워볼까요?</span>
        </div>

        {/* Login / CTA */}
        <div className="topnav-cta" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span
            onClick={goOnboarding}
            style={{
              fontSize: 14, fontWeight: 500, cursor: 'pointer',
              color: user ? '#fff' : '#d2d2da',
              transition: 'color .15s',
            }}
          >
            {displayName(user) || '로그인'}
          </span>
          <button
            onClick={goOnboarding}
            className="btn"
            style={{
              background: '#fff', color: '#E8123C',
              fontSize: 14, fontWeight: 700,
              padding: '8px 18px', borderRadius: 24,
            }}
          >
            {user ? '내 학습' : '시작하기'}
          </button>
        </div>

        {/* Burger — mobile only */}
        <button
          className="burger btn"
          onClick={() => navigate('/classes')}
          style={{
            width: 40, height: 40, display: 'none',
            alignItems: 'center', justifyContent: 'center',
            background: '#141419', borderRadius: 8,
            border: '1px solid rgba(255,255,255,.08)',
            color: '#fff', fontSize: 18,
          }}
        >
          ☰
        </button>
      </div>
    </header>
  )
}
