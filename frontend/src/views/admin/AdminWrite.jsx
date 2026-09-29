import { useState } from 'react'
import { Link } from 'react-router-dom'
import FilterChips from '../../components/FilterChips'
import RichEditor from '../../components/RichEditor'
import { createAuthoredArticle, uploadArticleImage } from '../../api/client'

const FORMATS = [
  { value: 'newsletter', label: '뉴스레터' },
  { value: 'column', label: '컬럼' },
  { value: 'guide', label: '가이드' },
]

function hasBody(html) {
  const text = html.replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ').trim()
  return text.length > 0 || html.includes('<img')
}

export default function AdminWrite() {
  const [articleType, setArticleType] = useState('newsletter')
  const [title, setTitle] = useState('')
  const [summary, setSummary] = useState('')
  const [html, setHtml] = useState('')
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(null)
  const [saving, setSaving] = useState(false)
  const [editorKey, setEditorKey] = useState(0)

  const publish = async (event) => {
    event.preventDefault()
    setError('')
    setSaved(null)
    if (!title.trim()) {
      setError('제목을 입력해 주세요.')
      return
    }
    if (!hasBody(html)) {
      setError('본문을 입력해 주세요.')
      return
    }
    setSaving(true)
    try {
      const article = await createAuthoredArticle({
        articleType,
        title: title.trim(),
        summary: summary.trim(),
        bodyHtml: html,
      })
      setSaved(article)
      setTitle('')
      setSummary('')
      setHtml('')
      setEditorKey(key => key + 1)
    } catch (err) {
      setError(err.message || '글을 저장하지 못했습니다.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={publish}>
      <h1 className="admin-title">글쓰기</h1>
      <p className="admin-lead">발행 후 24시간 동안 큐레이션의 해당 카테고리 맨 앞에 노출됩니다.</p>
      <FilterChips
        options={FORMATS}
        value={articleType}
        onChange={setArticleType}
        ariaLabel="글 카테고리"
        style={{ marginBottom: 18 }}
      />
      <label className="admin-field">
        <span>제목</span>
        <input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={300} />
      </label>
      <label className="admin-field">
        <span>요약</span>
        <textarea value={summary} onChange={(event) => setSummary(event.target.value)} maxLength={500} />
      </label>
      <div className="admin-field">
        <span>본문</span>
        <RichEditor key={editorKey} onChange={setHtml} uploadImage={uploadArticleImage} />
      </div>
      {error && <p role="alert" className="admin-error">{error}</p>}
      {saved && (
        <p className="admin-ok">
          발행했습니다. <Link to={saved.linkUrl || `/articles/${saved.id}`}>글 보기</Link>
        </p>
      )}
      <button className="admin-publish" type="submit" disabled={saving}>
        {saving ? '발행 중...' : '발행'}
      </button>
    </form>
  )
}
