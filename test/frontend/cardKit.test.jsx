import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ExternalCard } from '../../frontend/src/components/cardKit'

// 보안 LOW: 서버가 안전하지 않은 외부 링크(javascript: 등)를 null 로 거르면 카드는 링크 없이 그려진다
describe('ExternalCard', () => {
  it('href 가 있으면 새 탭 링크 셸', () => {
    render(<ExternalCard href="https://brunch.co.kr/x" testId="ext">본문</ExternalCard>)
    const card = screen.getByTestId('ext')
    expect(card.tagName).toBe('A')
    expect(card).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('href 가 없으면 링크가 아닌 div 셸로 내용만 보여 준다', () => {
    render(<ExternalCard href={null} testId="ext">본문</ExternalCard>)
    const card = screen.getByTestId('ext')
    expect(card.tagName).toBe('DIV')
    expect(card).not.toHaveAttribute('href')
    expect(card).toHaveTextContent('본문')
  })
})
