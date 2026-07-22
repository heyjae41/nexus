// 비밀번호 정책: 영문·숫자 포함 8자 이상 — 특수문자·대소문자 조합은 선택 (백엔드와 동일 규칙)
const PASSWORD_RULES = [
  { label: '8자 이상', test: (pw) => pw.length >= 8 },
  { label: '영문', test: (pw) => /[A-Za-z]/.test(pw) },
  { label: '숫자', test: (pw) => /\d/.test(pw) },
]

export function passwordMissing(pw) {
  return PASSWORD_RULES.filter(r => !r.test(pw || '')).map(r => r.label)
}
