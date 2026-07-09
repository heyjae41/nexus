// 커뮤니티 E2E: 회원(로그인) 상태에서 글쓰기 → 목록/상세 반영, 비로그인 온보딩 유도
import { expect, test } from '@playwright/test'

test('비로그인: 글쓰기 버튼은 온보딩으로 유도한다 (알럿 없음)', async ({ page }) => {
  await page.goto('/community')
  page.on('dialog', () => { throw new Error('브라우저 알럿이 떠서는 안 된다') })
  await page.getByRole('button', { name: /글쓰기/ }).click()
  await expect(page).toHaveURL(/\/onboarding/)
})

test('로그인 회원: 글쓰기 → 상세 이동 → 목록 즉시 반영', async ({ page, request }) => {
  // 회원 등록 후 로그인 상태 구성 (온보딩 완료와 동일한 저장 형태)
  const res = await request.post('http://localhost:8000/api/members', {
    data: { nickname: 'E2E테스터', role: '개발자' },
  })
  const member = (await res.json()).data
  await page.goto('/')
  await page.evaluate(
    (u) => localStorage.setItem('nexus.user', JSON.stringify(u)),
    { id: member.id, nickname: member.nickname, role: member.role },
  )

  const title = `E2E 글쓰기 검증 ${Date.now()}`
  await page.goto('/community')
  await page.getByRole('button', { name: /글쓰기/ }).click()
  await expect(page).toHaveURL(/\/community\/write/)

  await page.getByRole('button', { name: '질문' }).click()
  await page.getByPlaceholder(/제목/).fill(title)
  await page.locator('textarea').fill('플레이라이트로 작성한 본문입니다.')
  await page.getByRole('button', { name: /등록/ }).click()

  // 상세 페이지로 이동되고 본문이 보인다
  await expect(page).toHaveURL(/\/community\/\d+/)
  await expect(page.getByText(title)).toBeVisible()

  // 목록에 즉시 반영된다 (캐시 무효화 검증)
  await page.goto('/community')
  await expect(page.getByText(title)).toBeVisible()
})
