/* API client — proxied via Vite to localhost:8000 */
const BASE = import.meta.env.VITE_API_BASE || ''
const HOTPICK_API = 'https://open.paybooc.co.kr/bcai/api/hotpick/hotpicks'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, { credentials: 'include', ...options })
  if (!res.ok) {
    let message = `API error ${res.status}: ${path}`
    try {
      const body = await res.json()
      if (body?.error) message = body.error
    } catch {}
    throw new Error(message)
  }
  return res.json()
}

async function requestJson(path, method, body) {
  const json = await request(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return json.data ?? json
}

export async function checkNickname(nickname) {
  const params = new URLSearchParams({ nickname })
  const json = await request(`/api/auth/nickname-available?${params}`)
  return json.data ?? json
}

export async function registerAccount({ nickname, password, role, interests }) {
  return requestJson('/api/auth/register', 'POST', { nickname, password, role, interests })
}

export async function loginMember({ nickname, password }) {
  return requestJson('/api/auth/login', 'POST', { nickname, password })
}

export async function fetchCurrentMember() {
  const json = await request('/api/auth/me')
  return json.data ?? json
}

export async function updateCurrentMember(patch) {
  return requestJson('/api/auth/me', 'PATCH', patch)
}

export async function logoutMember() {
  const json = await request('/api/auth/logout', { method: 'POST' })
  return json.data ?? json
}

export async function deleteCurrentMember() {
  const json = await request('/api/auth/me', { method: 'DELETE' })
  return json.data ?? json
}

export async function fetchHome() {
  const json = await request('/api/home')
  return json.data ?? json
}

export async function fetchArticles({ category = 'curation', type = null, page = 1, size = 20 } = {}) {
  const params = new URLSearchParams({ category, page, size })
  if (type) params.set('type', type)
  const json = await request(`/api/articles?${params}`)
  return json
}

export async function fetchArticle(id) {
  const json = await request(`/api/articles/${id}`)
  return json.data ?? json
}

export async function likeArticle(id) {
  const json = await request(`/api/articles/${id}/like`, { method: 'POST' })
  return json.data ?? json
}

export async function fetchClasses({ category = null, page = 1, size = 20 } = {}) {
  const params = new URLSearchParams({ page, size })
  if (category) params.set('category', category)
  return request(`/api/classes?${params}`)
}

export async function fetchEvents({ category = null, page = 1, size = 20 } = {}) {
  const params = new URLSearchParams({ page, size })
  if (category) params.set('category', category)
  const json = await request(`/api/events?${params}`)
  return json
}

export async function fetchCardBenefits({ company = null, signal } = {}) {
  const params = new URLSearchParams()
  if (company) params.set('company', company)
  const query = params.toString()
  const json = await request(`/api/card-benefits${query ? `?${query}` : ''}`, { signal })
  return json.data ?? []
}

export async function fetchHotpicks({ signal } = {}) {
  const res = await fetch(HOTPICK_API, { cache: 'no-store', signal })
  if (!res.ok) throw new Error(`핫픽 API 오류 ${res.status}`)
  const json = await res.json()
  if (!Array.isArray(json?.posts)) throw new Error('핫픽 API 응답 형식이 올바르지 않습니다')
  return json
}

export async function registerMember({ nickname, password, role, interests } = {}) {
  // 신규 닉네임=가입, 기존 닉네임=로그인(비밀번호 검증, 불일치 시 401 에러 메시지)
  return requestJson('/api/members', 'POST', { nickname, password, role, interests })
}

export async function fetchMember(id) {
  const json = await request(`/api/members/${id}`)
  return json.data ?? json
}

export async function updateMember(id, patch) {
  return requestJson(`/api/members/${id}`, 'PATCH', patch)
}

export async function deleteMember(id) {
  const json = await request(`/api/members/${id}`, { method: 'DELETE' })
  return json.data ?? json
}

export async function fetchPosts({ tag = null, page = 1, size = 20 } = {}) {
  const params = new URLSearchParams({ page, size })
  if (tag) params.set('tag', tag)
  const json = await request(`/api/community/posts?${params}`)
  return json
}

export async function fetchPost(id) {
  const json = await request(`/api/community/posts/${id}`)
  return json.data ?? json
}

export async function createPost({ memberId, tag, title, body } = {}) {
  return requestJson('/api/community/posts', 'POST', { memberId, tag, title, body })
}

export async function createComment(postId, { memberId, body } = {}) {
  return requestJson(`/api/community/posts/${postId}/comments`, 'POST', { memberId, body })
}

export async function likePost(postId, memberId) {
  return requestJson(`/api/community/posts/${postId}/like`, 'POST', { memberId })
}
