/* 회원 표시명 — 신형(객체 {id, nickname, role})과 레거시(닉네임 문자열) 모두 지원 */
export function displayName(user) {
  if (!user) return null
  return typeof user === 'string' ? user : user.nickname
}
