// 커뮤니티 E2E: 회원(로그인) 상태에서 글쓰기 → 목록/상세 반영, 비로그인 온보딩 유도
import { expect, test } from '@playwright/test'

const API = process.env.E2E_API || 'http://localhost:8000'

test('비로그인: 글쓰기 버튼은 온보딩으로 유도한다 (알럿 없음)', async ({ page }) => {
  await page.goto('/community')
  page.on('dialog', () => { throw new Error('브라우저 알럿이 떠서는 안 된다') })
  await page.getByRole('button', { name: /글쓰기/ }).click()
  await expect(page).toHaveURL(/\/onboarding/)
})

test('로그인 회원: 글쓰기 → 상세 이동 → 목록 즉시 반영', async ({ page }) => {
  // 회원 등록 — 응답의 세션 쿠키가 브라우저 컨텍스트에 공유되어 로그인 상태가 된다
  const res = await page.request.post(`${API}/api/members`, {
    data: { nickname: 'E2E테스터', password: 'E2e!pass99', role: '개발자' },
  })
  const member = (await res.json()).data
  let postId = null
  try {
    const title = `E2E 글쓰기 검증 ${Date.now()}`
    await page.goto('/community')
    // 서버 세션 복원(/api/auth/me)이 끝나 상단에 닉네임이 떠야 로그인 상태다
    await expect(page.getByRole('link', { name: member.nickname })).toBeVisible()
    await page.getByRole('button', { name: /글쓰기/ }).click()
    await expect(page).toHaveURL(/\/community\/write/)

    await page.getByRole('button', { name: '자료', exact: true }).click()
    await page.getByPlaceholder(/제목/).fill(title)
    await page.locator('textarea').fill('플레이라이트로 작성한 본문입니다.')
    await page.getByRole('button', { name: /등록/ }).click()

    // 상세 페이지로 이동되고 본문이 보인다
    await expect(page).toHaveURL(/\/community\/\d+/)
    postId = page.url().match(/\/community\/(\d+)/)?.[1] ?? null
    await expect(page.getByText(title)).toBeVisible()

    // 목록에 즉시 반영된다 (캐시 무효화 검증)
    await page.goto('/community')
    await expect(page.getByText(title)).toBeVisible()
  } finally {
    // 정리: 생성한 글/회원을 제거해 dev DB 에 테스트 데이터가 누적되지 않게 한다
    if (postId) {
      await page.request.delete(`${API}/api/community/posts/${postId}`, {
        data: { memberId: member.id, password: 'E2e!pass99' },
      })
    }
    await page.request.delete(`${API}/api/members/${member.id}`)
  }
})
