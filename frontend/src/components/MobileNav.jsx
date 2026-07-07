import { useNavigate, useLocation } from 'react-router-dom'

const ITEMS = [
  { label: '홈', icon: '⌂', path: '/' },
  { label: '클래스', icon: '▦', path: '/classes' },
  { label: '커뮤니티', icon: '✎', path: '/community' },
  { label: 'meet.pl', icon: '◎', path: '/meet' },
  { label: 'MY', icon: '☰', path: '/dashboard' },
]

export default function MobileNav({ user: _user }) {
  const navigate = useNavigate()
  const { pathname } = useLocation()

  return (
    <nav
      className="mobnav"
      style={{
        position: 'fixed', bottom: 0, left: 0, right: 0,
        zIndex: 60,
        background: 'rgba(10,10,14,.96)',
        backdropFilter: 'blur(14px)',
        WebkitBackdropFilter: 'blur(14px)',
        borderTop: '1px solid rgba(255,255,255,.08)',
        display: 'flex',
        justifyContent: 'space-around',
        alignItems: 'center',
        padding: '8px 0 12px',
      }}
    >
      {ITEMS.map(item => {
        const active = item.path === '/' ? pathname === '/' : pathname.startsWith(item.path)
        return (
          <button
            key={item.path}
            onClick={() => navigate(item.path)}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
              background: 'none', border: 'none', cursor: 'pointer',
              color: active ? '#E8123C' : '#7a7a84',
              padding: '4px 12px',
              transition: 'color .15s',
            }}
          >
            <span style={{ fontSize: 20 }}>{item.icon}</span>
            <span style={{ fontSize: 10.5, fontWeight: 600 }}>{item.label}</span>
          </button>
        )
      })}
    </nav>
  )
}
