import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ArticleDetail from '@/views/ArticleDetail'
import AdminWrite from '@/views/admin/AdminWrite'

vi.mock('@/styles/article.css', () => ({}))
vi.mock('@/styles/admin.css', () => ({}))
vi.mock('@/components/KeyVisual', () => ({
  default: () => <div data-testid="key-visual" />,
}))
vi.mock('@/components/RichEditor', () => ({
  default: function MockEditor({ onChange, initialHtml = '' }) {
    return (
      <textarea
        aria-label="본문"
        defaultValue={initialHtml}
        onChange={(event) => onChange(event.target.value)}
      />
    )
  },
}))
vi.mock('@/api/client', () => ({
  fetchArticle: vi.fn(),
  fetchArticles: vi.fn(),
  likeArticle: vi.fn(),
  createAuthoredArticle: vi.fn(),
  uploadArticleImage: vi.fn(),
  updateAuthoredArticle: vi.fn(),
}))

import { fetchArticle, fetchArticles, updateAuthoredArticle } from '@/api/client'

const authored = {
  id: 7,
  articleType: 'column',
  title: '내가 쓴 컬럼',
  summary: '요약',
  authorName: '운영자',
  sourceType: 'authored',
  readMinutes: 2,
  likesCount: 1,
  viewCount: 3,
  publishedAt: '2026-09-30T00:00:00+00:00',
  isExternal: false,
  bodyHtml: '<p>원래 본문</p>',
}

function detail(user) {
  return render(
    <MemoryRouter initialEntries={['/articles/7']}>
      <Routes>
        <Route path="/articles/:id" element={<ArticleDetail user={user} />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('내 글 수정', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    fetchArticle.mockResolvedValue(authored)
    fetchArticles.mockResolvedValue({ data: [], articles: [] })
  })

  it('작성자에게 수정 버튼을 보여 준다', async () => {
    detail({ nickname: '운영자', accessRole: 'admin' })
    expect(await screen.findByRole('link', { name: '수정' })).toHaveAttribute('href', '/articles/7/edit')
  })

  it('다른 사람과 수집 글에는 수정 버튼을 보여 주지 않는다', async () => {
    detail({ nickname: '다른사람', accessRole: 'admin' })
    await screen.findByRole('button', { name: /좋아요/ })
    expect(screen.queryByRole('link', { name: '수정' })).not.toBeInTheDocument()

    fetchArticle.mockResolvedValue({ ...authored, sourceType: 'brunch', authorName: '운영자' })
    detail({ nickname: '운영자', accessRole: 'admin' })
    await screen.findByRole('heading', { name: '내가 쓴 컬럼' })
    expect(screen.queryByRole('link', { name: '수정' })).not.toBeInTheDocument()
  })

  it('작성자가 제목과 본문을 고쳐 저장한다', async () => {
    updateAuthoredArticle.mockResolvedValue({ ...authored, title: '고친 제목', linkUrl: '/articles/7' })
    const ue = userEvent.setup()
    render(
      <MemoryRouter>
        <AdminWrite articleId="7" user={{ nickname: '운영자', accessRole: 'admin' }} />
      </MemoryRouter>,
    )
    const title = await screen.findByRole('textbox', { name: '제목' })
    expect(title).toHaveValue('내가 쓴 컬럼')
    await ue.clear(title)
    await ue.type(title, '고친 제목')
    await ue.click(screen.getByRole('button', { name: '저장' }))
    await waitFor(() => expect(updateAuthoredArticle).toHaveBeenCalledWith('7', {
      articleType: 'column',
      title: '고친 제목',
      summary: '요약',
      bodyHtml: '<p>원래 본문</p>',
    }))
    expect(screen.getByRole('link', { name: '글 보기' })).toHaveAttribute('href', '/articles/7')
  })
})
