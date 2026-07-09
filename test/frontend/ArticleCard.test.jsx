/**
 * Tests for the CRITICAL LINK RULE:
 * - isExternal === true  → <a href={linkUrl} target="_blank" rel="noopener noreferrer">
 * - isExternal === false → <Link to={/articles/:id}>
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import ArticleCard from '@/components/ArticleCard'

const wrap = (ui) => render(<BrowserRouter>{ui}</BrowserRouter>)

const baseArticle = {
  id: 'test-1',
  articleType: 'brunch',
  title: '브런치 외부 아티클',
  summary: '테스트 요약',
  authorName: '테스터',
  readMinutes: 5,
  likesCount: 10,
  commentsCount: 2,
  viewCount: 100,
  publishedAt: '2026-07-07',
  linkUrl: 'https://brunch.co.kr/@test/1?ref=nexus.bccard.ai',
  isExternal: false,
}

describe('ArticleCard — 썸네일', () => {
  it('thumbnailUrl 이 있으면 대표 이미지를 렌더링한다', () => {
    const { container } = wrap(
      <ArticleCard
        article={{ ...baseArticle, thumbnailUrl: 'https://t1.kakaocdn.net/brunch/cover.png' }}
        index={0}
      />,
    )
    const img = container.querySelector('img')
    expect(img).not.toBeNull()
    expect(img).toHaveAttribute('src', 'https://t1.kakaocdn.net/brunch/cover.png')
  })

  it('thumbnailUrl 이 없으면 이미지를 렌더링하지 않는다 (그라디언트 유지)', () => {
    const { container } = wrap(<ArticleCard article={baseArticle} index={0} />)
    expect(container.querySelector('img')).toBeNull()
  })

  it('list variant 에서도 썸네일을 렌더링한다', () => {
    const { container } = wrap(
      <ArticleCard
        article={{ ...baseArticle, thumbnailUrl: 'https://t1.kakaocdn.net/brunch/cover.png' }}
        index={0}
        variant="list"
      />,
    )
    const img = container.querySelector('img')
    expect(img).not.toBeNull()
    expect(img).toHaveAttribute('src', 'https://t1.kakaocdn.net/brunch/cover.png')
  })
})

describe('ArticleCard — CRITICAL LINK RULE', () => {
  it('renders an internal Link for isExternal=false', () => {
    wrap(<ArticleCard article={{ ...baseArticle, isExternal: false }} index={0} />)
    const link = screen.getByTestId('article-card-internal')
    expect(link).toBeInTheDocument()
    expect(link.tagName).toBe('A')
    expect(link).toHaveAttribute('href', '/articles/test-1')
    expect(link).not.toHaveAttribute('target')
  })

  it('renders an external <a> for isExternal=true (brunch article)', () => {
    wrap(<ArticleCard article={{ ...baseArticle, isExternal: true }} index={0} />)
    const link = screen.getByTestId('article-card-external')
    expect(link).toBeInTheDocument()
    expect(link.tagName).toBe('A')
    expect(link).toHaveAttribute('href', baseArticle.linkUrl)
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('does NOT use linkUrl for internal articles even if linkUrl is set', () => {
    const article = { ...baseArticle, isExternal: false, linkUrl: 'https://external.example.com' }
    wrap(<ArticleCard article={article} index={0} />)
    const link = screen.getByTestId('article-card-internal')
    expect(link).toHaveAttribute('href', '/articles/test-1')
    expect(link).not.toHaveAttribute('href', 'https://external.example.com')
  })

  it('shows title text in the card', () => {
    wrap(<ArticleCard article={baseArticle} index={0} />)
    expect(screen.getByText('브런치 외부 아티클')).toBeInTheDocument()
  })

  it('renders newsletter badge label as 뉴스레터', () => {
    const article = { ...baseArticle, articleType: 'newsletter', isExternal: false }
    wrap(<ArticleCard article={article} index={0} />)
    expect(screen.getByText('뉴스레터')).toBeInTheDocument()
  })

  it('renders brunch badge label as 브런치', () => {
    const article = { ...baseArticle, articleType: 'brunch', isExternal: true }
    wrap(<ArticleCard article={article} index={0} />)
    expect(screen.getByText('브런치')).toBeInTheDocument()
  })

  it('renders list variant without crashing', () => {
    wrap(<ArticleCard article={baseArticle} index={1} variant="list" />)
    expect(screen.getByText('브런치 외부 아티클')).toBeInTheDocument()
  })
})
