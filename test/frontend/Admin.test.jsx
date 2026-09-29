import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import Nav from '@/components/Nav'
import AdminShell from '@/views/admin/AdminShell'
import AdminWrite from '@/views/admin/AdminWrite'
import AdminPermissions from '@/views/admin/AdminPermissions'

vi.mock('@/components/RichEditor', () => ({
  default: function MockEditor({ onChange }) {
    return <textarea aria-label="본문" onChange={(event) => onChange(`<p>${event.target.value}</p>`)} />
  },
}))

vi.mock('@/api/client', () => ({
  createAuthoredArticle: vi.fn(),
  uploadArticleImage: vi.fn(),
  fetchAdminMembers: vi.fn(),
  updateMemberAccess: vi.fn(),
}))

import { createAuthoredArticle, fetchAdminMembers, updateMemberAccess } from '@/api/client'

describe('어드민 진입', () => {
  it('어드민에게만 우측 Admin 버튼을 보여 준다', () => {
    render(
      <MemoryRouter>
        <Nav user={{ nickname: '운영자', accessRole: 'admin' }} />
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: 'Admin' })).toHaveAttribute('href', '/admin/write')
  })

  it('일반 사용자에게는 Admin 버튼을 보여 주지 않는다', () => {
    render(
      <MemoryRouter>
        <Nav user={{ nickname: '일반', accessRole: 'user' }} />
      </MemoryRouter>,
    )
    expect(screen.queryByRole('link', { name: 'Admin' })).not.toBeInTheDocument()
  })

  it('Admin 화면 왼쪽에 권한관리와 글쓰기 메뉴를 둔다', () => {
    render(
      <MemoryRouter initialEntries={['/admin/write']}>
        <Routes>
          <Route path="/admin" element={<AdminShell user={{ nickname: '운영자', accessRole: 'admin' }} />}>
            <Route path="write" element={<AdminWrite />} />
            <Route path="permissions" element={<div>권한 화면</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: '권한관리' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '글쓰기' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '글쓰기' })).toBeInTheDocument()
  })
})

describe('어드민 글쓰기', () => {
  beforeEach(() => vi.clearAllMocks())

  it('선택한 카테고리와 본문을 발행한다', async () => {
    createAuthoredArticle.mockResolvedValue({ id: 9, linkUrl: '/articles/9' })
    const ue = userEvent.setup()
    render(
      <MemoryRouter>
        <AdminWrite />
      </MemoryRouter>,
    )
    await ue.click(screen.getByRole('button', { name: '컬럼' }))
    await ue.type(screen.getByRole('textbox', { name: '제목' }), '직접 쓴 컬럼')
    await ue.type(screen.getByRole('textbox', { name: '본문' }), '본문 내용')
    await ue.click(screen.getByRole('button', { name: '발행' }))
    await waitFor(() => expect(createAuthoredArticle).toHaveBeenCalledWith({
      articleType: 'column',
      title: '직접 쓴 컬럼',
      summary: '',
      bodyHtml: '<p>본문 내용</p>',
    }))
    expect(screen.getByRole('link', { name: '글 보기' })).toHaveAttribute('href', '/articles/9')
  })
})

describe('권한관리', () => {
  beforeEach(() => vi.clearAllMocks())

  it('사용자를 어드민으로 바꾼다', async () => {
    fetchAdminMembers.mockResolvedValue([{ id: 2, nickname: '일반', accessRole: 'user' }])
    updateMemberAccess.mockResolvedValue({ id: 2, nickname: '일반', accessRole: 'admin' })
    const ue = userEvent.setup()
    render(
      <MemoryRouter>
        <AdminPermissions />
      </MemoryRouter>,
    )
    const select = await screen.findByRole('combobox', { name: '일반 권한' })
    await ue.selectOptions(select, 'admin')
    await waitFor(() => expect(updateMemberAccess).toHaveBeenCalledWith(2, 'admin'))
    expect(select).toHaveValue('admin')
  })
})
