function imageSources(html) {
  return [...(html || '').matchAll(/<img\b[^>]*\bsrc\s*=\s*["']([^"']+)["']/gi)].map(match => match[1])
}

function isStoredMedia(src) {
  if (src.startsWith('/api/media/') && !src.includes('..')) return true
  try {
    const url = new URL(src)
    return url.pathname.startsWith('/api/media/') && !url.pathname.includes('..')
  } catch {
    return false
  }
}

export function hasUnstoredImage(html) {
  return imageSources(html).some(src => !isStoredMedia(src))
}
