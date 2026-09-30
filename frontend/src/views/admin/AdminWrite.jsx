import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import FilterChips from '../../components/FilterChips'
import RichEditor from '../../components/RichEditor'
import {
  createAuthoredArticle,
  fetchArticle,
  updateAuthoredArticle,
  uploadArticleImage,
} from '../../api/client'
import '../../styles/admin.css'
import { hasUnstoredImage } from './articleImages'

const FORMATS = [
  { value: 'newsletter', label: '뉴스레터' },
  { value: 'column', label: '컬럼' },
  { value: 'guide', label: '가이드' },
]

function hasBody(html) {
  const text = html.replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ').trim()
  return text.length > 0 || html.includes('<img')
}

export default function AdminWrite({ articleId = null, user = null }) {
  const editing = articleId != null
  const [articleType, setArticleType] = useState('newsletter')
  const [title, setTitle] = useState('')
  const [summary, setSummary] = useState('')
  const [html, setHtml] = useState('')
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(null)
  const [saving, setSaving] = useState(false)
  const [editorKey, setEditorKey] = useState(0)
  const [ready, setReady] = useState(!editing)
  const [blocked, setBlocked] = useState('')
  const [uploading, setUploading] = useState(false)
  const htmlRef = useRef('')

  useEffect(() => {
    if (!editing) return undefined
    let active = true
    setReady(false)
    setBlocked('')
    setError('')
    fetchArticle(articleId)
      .then((article) => {
        if (!active) return
        const mine = article?.sourceType === 'authored' && article?.authorName === user?.nickname
        if (!mine) {
          setBlocked('이 글을 수정할 수 없습니다.')
          return
        }
        setArticleType(article.articleType || 'newsletter')
        setTitle(article.title || '')
        setSummary(article.summary || '')
        htmlRef.current = article.bodyHtml || ''
        setHtml(article.bodyHtml || '')
      })
      .catch((err) => {
        if (active) setBlocked(err.message || '글을 불러오지 못했습니다.')
      })
      .finally(() => {
        if (active) setReady(true)
      })
    return () => { active = false }
  }, [articleId, editing, user])

  const publish = async (event) => {
    event.preventDefault()
    setError('')
    setSaved(null)
    if (!title.trim()) {
      setError('제목을 입력해 주세요.')
      return
    }
    const bodyHtml = htmlRef.current
    if (!hasBody(bodyHtml)) {
      setError('본문을 입력해 주세요.')
      return
    }
    if (hasUnstoredImage(bodyHtml)) {
      setError('웹에서 붙여 넣은 이미지는 저장되지 않습니다. 이미지 버튼으로 파일을 올려 주세요.')
      return
    }
    const payload = {
      articleType,
      title: title.trim(),
      summary: summary.trim(),
      bodyHtml,
    }
    setSaving(true)
    try {
      const article = editing
        ? await updateAuthoredArticle(articleId, payload)
        : await createAuthoredArticle(payload)
      setSaved(article)
      if (!editing) {
        setTitle('')
        setSummary('')
        htmlRef.current = ''
        setHtml('')
        setEditorKey(key => key + 1)
      }
    } catch (err) {
      setError(err.message || '글을 저장하지 못했습니다.')
    } finally {
      setSaving(false)
    }
  }

  const frame = (child) => (
    editing ? <main className="admin-main" style={{ maxWidth: 860, margin: '0 auto' }}>{child}</main> : child
  )

  if (!ready) return frame(<p className="admin-lead">불러오는 중...</p>)
  if (blocked) return frame(<p role="alert" className="admin-error">{blocked}</p>)

  return frame(
    <form onSubmit={publish}>
      <h1 className="admin-title">{editing ? '글 수정' : '글쓰기'}</h1>
      <p className="admin-lead">
        {editing
          ? '수정한 내용은 바로 글에 반영됩니다.'
          : '발행 후 24시간 동안 큐레이션의 해당 카테고리 맨 앞에 노출됩니다.'}
      </p>
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
        <RichEditor
          key={`${articleId || 'new'}-${editorKey}`}
          initialHtml={html}
          onChange={(next) => { htmlRef.current = next; setHtml(next) }}
          onUploading={setUploading}
          uploadImage={uploadArticleImage}
        />
      </div>
      {error && <p role="alert" className="admin-error">{error}</p>}
      {saved && (
        <p className="admin-ok">
          {editing ? '수정했습니다.' : '발행했습니다.'}{' '}
          <Link to={saved.linkUrl || `/articles/${saved.id}`}>글 보기</Link>
        </p>
      )}
      <button className="admin-publish" type="submit" disabled={saving || uploading}>
        {saving ? (editing ? '저장 중...' : '발행 중...') : (editing ? '저장' : '발행')}
      </button>
    </form>,
  )
}

export function ArticleEdit({ user }) {
  const { id } = useParams()
  return <AdminWrite articleId={id} user={user} />
}
