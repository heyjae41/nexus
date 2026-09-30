import { NavLink, Outlet } from 'react-router-dom'
import '../../styles/admin.css'

export default function AdminShell({ user }) {
  const writer = user?.accessRole === 'admin'
  const superAdmin = Boolean(user?.superAdmin)
  if (!writer && !superAdmin) {
    return (
      <main className="admin-denied">
        <p>어드민 권한이 필요합니다.</p>
      </main>
    )
  }
  const menus = [
    superAdmin ? { to: '/admin/permissions', label: '권한관리' } : null,
    writer ? { to: '/admin/write', label: '글쓰기' } : null,
  ].filter(Boolean)
  return (
    <div className="admin-shell">
      <aside className="admin-side" aria-label="어드민 메뉴">
        {menus.map(menu => (
          <NavLink key={menu.to} to={menu.to} className={({ isActive }) => (isActive ? 'active' : undefined)}>
            {menu.label}
          </NavLink>
        ))}
      </aside>
      <div className="admin-main">
        <Outlet />
      </div>
    </div>
  )
}
