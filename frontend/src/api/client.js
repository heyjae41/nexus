/* API client — proxied via Vite to localhost:8000 */
const BASE = import.meta.env.VITE_API_BASE || ''

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${path}`)
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
