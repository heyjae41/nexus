import { Link, useLocation } from 'react-router-dom'

const ITEMS = [
  { label: '홈', icon: '⌂', path: '/' },
  { label: '클래스', icon: '▦', path: '/classes' },
  { label: '커뮤니티', icon: '✎', path: '/community' },
  { label: 'meet.pl', icon: '◎', path: '/meet' },
]

const itemStyle = active => ({
  display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 3,
  background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'none',
  color: active ? '#E8123C' : '#7a7a84',
  minWidth: 54, minHeight: 48, padding: '4px 8px', transition: 'color .15s',
})

function ItemContent({ icon, label }) {
  return (
    <>
      <span aria-hidden="true" style={{ fontSize: 20 }}>{icon}</span>
      <span style={{ fontSize: 10.5, fontWeight: 600 }}>{label}</span>
    </>
  )
}

export default function MobileNav({ user, onLogin }) {
  const { pathname } = useLocation()

  return (
    <nav
      className="mobnav"
      aria-label="모바일 하단 메뉴"
      style={{
        position: 'fixed', bottom: 0, left: 0, right: 0,
        zIndex: 60,
        background: 'rgba(10,10,14,.96)',
        backdropFilter: 'blur(14px)',
        WebkitBackdropFilter: 'blur(14px)',
        borderTop: '1px solid rgba(255,255,255,.08)',
        justifyContent: 'space-around',
        alignItems: 'center',
        padding: '6px max(4px, env(safe-area-inset-right)) calc(8px + env(safe-area-inset-bottom)) max(4px, env(safe-area-inset-left))',
      }}
    >
      {ITEMS.map(item => {
        const active = item.path === '/' ? pathname === '/' : pathname.startsWith(item.path)
        return (
          <Link key={item.path} to={item.path} aria-label={item.label} aria-current={active ? 'page' : undefined} style={itemStyle(active)}>
            <ItemContent icon={item.icon} label={item.label} />
          </Link>
        )
      })}
      {user ? (
        <Link to="/profile" aria-label="MY 내 정보" aria-current={pathname.startsWith('/profile') ? 'page' : undefined} style={itemStyle(pathname.startsWith('/profile'))}>
          <ItemContent icon="◉" label="MY" />
        </Link>
      ) : (
        <button type="button" aria-label="MY 로그인" onClick={onLogin} style={itemStyle(false)}>
          <ItemContent icon="◉" label="MY" />
        </button>
      )}
    </nav>
  )
}
