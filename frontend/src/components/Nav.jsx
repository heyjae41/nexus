import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation, Link } from 'react-router-dom'
import { displayName } from '../utils/user'
import { useModalA11y } from '../hooks/useModalA11y'

export const NAV_LINKS = [
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

export default function Nav({ user, onLogin, onLogout }) {
  const { pathname } = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState('')
  const burgerRef = useRef(null)
  const menuPanelRef = useRef(null)
  const closeButtonRef = useRef(null)

  useEffect(() => { setMenuOpen(false) }, [pathname])

  const closeMenu = useCallback(() => setMenuOpen(false), [])
  useModalA11y({
    active: menuOpen,
    containerRef: menuPanelRef,
    onClose: closeMenu,
    initialFocusRef: closeButtonRef,
  })

  const logout = async () => {
    setLoggingOut(true)
    setLogoutError('')
    try {
      await onLogout?.()
      setMenuOpen(false)
    } catch {
      setLogoutError('로그아웃하지 못했습니다. 잠시 후 다시 시도해 주세요.')
    } finally {
      setLoggingOut(false)
    }
  }


  return (
    <>
    <header className="site-header" style={{
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
          <span style={{ fontSize: 21, fontWeight: 800, color: '#fff', letterSpacing: '-.03em' }}>EDU.AI</span>
        </Link>

        {/* Nav links */}
        <nav className="topnav-links" style={{ display: 'flex', alignItems: 'center', gap: 22 }}>
          {NAV_LINKS.map(link => (
            <Link
              key={link.path}
              to={link.path}
              aria-current={isActive(pathname, link.match) ? 'page' : undefined}
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
            href="https://web.paybooc.ai/place/eatpl-home"
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontSize: 14.5, fontWeight: 600, color: '#a6a6b0', textDecoration: 'none' }}
          >
            eat.pl ↗
          </a>
          <Link
            to="/cardpick"
            aria-current={isActive(pathname, ['/cardpick']) ? 'page' : undefined}
            style={{
              fontSize: 14.5, fontWeight: 600, letterSpacing: '-.01em',
              color: isActive(pathname, ['/cardpick']) ? '#E8123C' : '#a6a6b0',
              textDecoration: 'none',
              transition: 'color .15s',
            }}
          >
            card.Pick
          </Link>
        </nav>

        <div style={{ flex: 1 }} />

        {/* Login — 중복 CTA 없이 로그인 또는 닉네임 하나만 표시 */}
        <div className="topnav-cta">
          {user ? (
            <Link to="/profile" style={{ color: '#fff', fontSize: 14, fontWeight: 700, textDecoration: 'none' }}>
              {displayName(user)}
            </Link>
          ) : (
            <button className="btn" onClick={onLogin} style={{
              background: '#fff', color: '#E8123C', fontSize: 14, fontWeight: 700,
              padding: '8px 18px', borderRadius: 24,
            }}>
              로그인
            </button>
          )}
        </div>

        {/* Burger — mobile only */}
        <button
          ref={burgerRef}
          className="burger btn"
          type="button"
          aria-label={menuOpen ? '전체 메뉴 닫기' : '전체 메뉴 열기'}
          aria-expanded={menuOpen}
          aria-controls="mobile-menu-dialog"
          onClick={() => { setLogoutError(''); setMenuOpen(open => !open) }}
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
    {menuOpen && (
      <div id="mobile-menu-dialog" className="mobile-menu-layer" role="dialog" aria-modal="true" aria-label="모바일 메뉴">
        <button type="button" tabIndex={-1} className="mobile-menu-backdrop" aria-label="모바일 메뉴 닫기" onClick={() => setMenuOpen(false)} />
        <aside ref={menuPanelRef} className="mobile-menu-panel">
          <div className="mobile-menu-head">
            <strong>전체 메뉴</strong>
            <button ref={closeButtonRef} type="button" className="btn mobile-menu-close" aria-label="모바일 메뉴 닫기" onClick={() => setMenuOpen(false)}>×</button>
          </div>
          <nav aria-label="모바일 전체 메뉴" className="mobile-menu-links">
            {NAV_LINKS.map(link => (
              <Link key={link.path} to={link.path} onClick={() => setMenuOpen(false)} aria-current={isActive(pathname, link.match) ? 'page' : undefined} className={isActive(pathname, link.match) ? 'active' : ''}>
                <span>{link.label}</span><span aria-hidden="true">›</span>
              </Link>
            ))}
            <a href="https://web.paybooc.ai/place/eatpl-home" target="_blank" rel="noopener noreferrer" onClick={() => setMenuOpen(false)}>
              <span>eat.pl</span><span aria-hidden="true">↗</span>
            </a>
            <Link to="/cardpick" onClick={() => setMenuOpen(false)} aria-current={isActive(pathname, ['/cardpick']) ? 'page' : undefined} className={isActive(pathname, ['/cardpick']) ? 'active' : ''}>
              <span>card.Pick</span><span aria-hidden="true">›</span>
            </Link>
          </nav>
          <div className="mobile-menu-account">
            {user ? (
              <>
                <Link to="/profile" onClick={() => setMenuOpen(false)} aria-label={`${displayName(user)} 내 정보`} className="mobile-profile-link">
                  <span className="mobile-profile-avatar">{displayName(user).slice(0, 1)}</span>
                  <span><small>로그인 중</small><strong>{displayName(user)}</strong></span>
                </Link>
                <button type="button" className="btn mobile-logout" disabled={loggingOut} onClick={logout}>{loggingOut ? '로그아웃 중...' : '로그아웃'}</button>
                {logoutError && <p role="alert" className="mobile-logout-error">{logoutError}</p>}
              </>
            ) : (
              <button type="button" className="btn mobile-login" onClick={() => { setMenuOpen(false); onLogin?.() }}>로그인하기</button>
            )}
          </div>
        </aside>
      </div>
    )}
    </>
  )
}
