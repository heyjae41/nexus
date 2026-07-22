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

export async function checkNickname(nickname) {
  const params = new URLSearchParams({ nickname })
  const json = await request(`/api/auth/nickname-available?${params}`)
  return json.data ?? json
}

export async function registerAccount({ nickname, password, role, interests }) {
  const json = await request('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nickname, password, role, interests }),
  })
  return json.data ?? json
}

export async function loginMember({ nickname, password }) {
  const json = await request('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nickname, password }),
  })
  return json.data ?? json
}

export async function fetchCurrentMember() {
  const json = await request('/api/auth/me')
  return json.data ?? json
}

export async function updateCurrentMember(patch) {
  const json = await request('/api/auth/me', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
  return json.data ?? json
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

export async function fetchHotpicks({ signal } = {}) {
  const res = await fetch(HOTPICK_API, { cache: 'no-store', signal })
  if (!res.ok) throw new Error(`핫픽 API 오류 ${res.status}`)
  const json = await res.json()
  if (!Array.isArray(json?.posts)) throw new Error('핫픽 API 응답 형식이 올바르지 않습니다')
  return json
}

export async function registerMember({ nickname, password, role, interests } = {}) {
  // 신규 닉네임=가입, 기존 닉네임=로그인(비밀번호 검증, 불일치 시 401 에러 메시지)
  const json = await request('/api/members', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nickname, password, role, interests }),
  })
  return json.data ?? json
}

export async function fetchMember(id) {
  const json = await request(`/api/members/${id}`)
  return json.data ?? json
}

export async function updateMember(id, patch) {
  const json = await request(`/api/members/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
  return json.data ?? json
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
  const json = await request('/api/community/posts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ memberId, tag, title, body }),
  })
  return json.data ?? json
}

export async function createComment(postId, { memberId, body } = {}) {
  const json = await request(`/api/community/posts/${postId}/comments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ memberId, body }),
  })
  return json.data ?? json
}

export async function likePost(postId, memberId) {
  const json = await request(`/api/community/posts/${postId}/like`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ memberId }),
  })
  return json.data ?? json
}
