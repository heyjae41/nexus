// NEXUS E2E 스모크: 홈 → 큐레이션 → 상세 → 좋아요, 반응형(모바일) 확인
import { expect, test } from '@playwright/test'

test('홈: 히어로와 큐레이션 섹션이 렌더링된다', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('h1')).toContainText('금융 AI 한 스푼')
  await expect(page.getByRole('heading', { name: /나를 위한 큐레이션/ })).toBeVisible()
  // 카드가 내부 글(/articles/N)일 수도, 브런치 수집 글(외부 링크)일 수도 있다 — 데이터 비의존 셀렉터
  const cards = page.locator('a[href^="/articles/"], a[href*="brunch.co.kr"]')
  await expect(cards.first()).toBeVisible()
})

test('큐레이션 목록: DB 시드 글이 보인다', async ({ page }) => {
  await page.goto('/curation')
  await expect(page.getByText('회의록 요약, LLM에게 맡기는 법').first()).toBeVisible()
})

test('아티클 상세: 키비주얼·본문·좋아요가 동작한다', async ({ page }) => {
  await page.goto('/curation')
  await page.locator('a[href^="/articles/"]').first().click()
  await expect(page).toHaveURL(/\/articles\/\d+/)
  await expect(page.locator('svg').first()).toBeVisible() // 애니메이션 키비주얼
  const like = page.getByRole('button', { name: /좋아요|♥|❤/ }).first()
  const before = await like.textContent()
  await like.click()
  await expect(like).not.toHaveText(before, { timeout: 5000 })
})

test('반응형: 모바일 뷰포트에서 하단 네비가 표시된다', async ({ page }) => {
  await page.setViewportSize({ width: 400, height: 800 })
  await page.goto('/')
  await expect(page.locator('nav.mobnav, .mobnav').first()).toBeVisible()
})
