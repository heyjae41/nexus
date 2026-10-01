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

export async function fetchCardBenefits({ company = null, country = null, signal } = {}) {
  const params = new URLSearchParams()
  if (company) params.set('company', company)
  if (country) params.set('country', country)
  const query = params.toString()
  const json = await request(`/api/card-benefits${query ? `?${query}` : ''}`, { signal })
  // items: 혜택 목록 / countries: 국가 필터 칩 구성용 집계(meta)
  return { items: json.data ?? [], countries: json.meta?.countries ?? [] }
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

// 앞단(WAF)이 8192바이트를 넘는 요청 본문을 403으로 거절한다 — 사진과 긴 글 본문은
// 그 한도 아래 조각으로 나눠 보내고 서버가 조립한다. 글 본문 조각은 제목·요약 메타가
// 매 요청에 같이 실리므로 사진 조각보다 작게 잡는다.
const IMAGE_PART_BYTES = 5598
const ARTICLE_PART_BYTES_MAX = 3900 // 서버 BODY_CHUNK_RAW 와 같다
const PART_REQUEST_BUDGET = 8000 // WAF 한도 8192 에서 여유를 뺀 값

function bytesToBase64(bytes) {
  let binary = ''
  for (let i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i])
  return btoa(binary)
}

async function postInParts(path, bytes, partBytes, extra, onProgress) {
  const total = Math.max(1, Math.ceil(bytes.length / partBytes))
  const uploadId = crypto.randomUUID().replace(/-/g, '')
  let last = null
  for (let index = 0; index < total; index += 1) {
    const slice = bytes.subarray(index * partBytes, (index + 1) * partBytes)
    last = await requestJson(path, 'POST', {
      uploadId, index, total, data: bytesToBase64(slice), ...extra,
    })
    onProgress?.(index + 1, total)
  }
  return last
}

function articlePartBytes(extra) {
  // 제목·요약은 매 조각에 실리므로, 메타 봉투 크기를 실제로 재서 본문 조각 크기를 정한다
  const envelope = JSON.stringify({ ...extra, uploadId: 'x'.repeat(32), index: 9999, total: 9999, data: '' })
  const metaBytes = new TextEncoder().encode(envelope).length
  const raw = Math.floor((PART_REQUEST_BUDGET - metaBytes) / 4) * 3
  return Math.max(1024, Math.min(ARTICLE_PART_BYTES_MAX, raw))
}

async function saveArticleInParts({ articleId, articleType, title, summary, bodyHtml }) {
  const extra = { articleType, title, summary, ...(articleId == null ? {} : { articleId }) }
  const bytes = new TextEncoder().encode(bodyHtml ?? '')
  const saved = await postInParts('/api/admin/articles/parts', bytes, articlePartBytes(extra), extra)
  if (!saved?.id) throw new Error('글이 저장되지 않았습니다. 다시 시도해 주세요.')
  return saved
}

export async function createAuthoredArticle({ articleType, title, summary, bodyHtml }) {
  return saveArticleInParts({ articleType, title, summary, bodyHtml })
}

export async function updateAuthoredArticle(id, { articleType, title, summary, bodyHtml }) {
  return saveArticleInParts({ articleId: id, articleType, title, summary, bodyHtml })
}

export async function uploadArticleImage(file, onProgress) {
  const bytes = new Uint8Array(await file.arrayBuffer())
  const extra = { contentType: file.type || 'application/octet-stream' }
  const result = await postInParts('/api/admin/media/parts', bytes, IMAGE_PART_BYTES, extra, onProgress)
  if (!result?.url) throw new Error('이미지 주소를 받지 못했습니다.')
  return { url: result.url }
}

export async function fetchAdminMembers() {
  const json = await request('/api/admin/members')
  return json.data ?? []
}

export async function updateMemberAccess(id, accessRole) {
  return requestJson(`/api/admin/members/${id}`, 'PATCH', { accessRole })
}
