import { NavLink, Outlet } from 'react-router-dom'
import '../../styles/admin.css'

const MENUS = [
  { to: '/admin/permissions', label: '권한관리' },
  { to: '/admin/write', label: '글쓰기' },
]

export default function AdminShell({ user }) {
  if (user?.accessRole !== 'admin') {
    return (
      <main className="admin-denied">
        <p>어드민 권한이 필요합니다.</p>
      </main>
    )
  }
  return (
    <div className="admin-shell">
      <aside className="admin-side" aria-label="어드민 메뉴">
        {MENUS.map(menu => (
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
