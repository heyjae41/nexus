/* API client — proxied via Vite to localhost:8000 */
const BASE = import.meta.env.VITE_API_BASE || ''

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
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

export async function fetchHome() {
  const json = await request('/api/home')
  return json.data ?? json
}

export async function fetchArticles({ category = 'curation', page = 1, size = 20 } = {}) {
  const params = new URLSearchParams({ category, page, size })
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

export async function fetchEvents({ page = 1, size = 20 } = {}) {
  const params = new URLSearchParams({ page, size })
  const json = await request(`/api/events?${params}`)
  return json
}

export async function registerMember({ nickname, email, role, interests } = {}) {
  const json = await request('/api/members', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nickname, email, role, interests }),
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

export async function fetchPosts({ page = 1, size = 20 } = {}) {
  const params = new URLSearchParams({ page, size })
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
