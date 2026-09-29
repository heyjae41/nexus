import { useRef, useState } from 'react'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Image from '@tiptap/extension-image'
import Placeholder from '@tiptap/extension-placeholder'

const TOOLS = [
  { name: '굵게', mark: 'bold', run: (editor) => editor.chain().focus().toggleBold().run() },
  { name: '기울임', mark: 'italic', run: (editor) => editor.chain().focus().toggleItalic().run() },
  { name: '제목', mark: 'heading', run: (editor) => editor.chain().focus().toggleHeading({ level: 2 }).run() },
  { name: '목록', mark: 'bulletList', run: (editor) => editor.chain().focus().toggleBulletList().run() },
  { name: '번호', mark: 'orderedList', run: (editor) => editor.chain().focus().toggleOrderedList().run() },
  { name: '인용', mark: 'blockquote', run: (editor) => editor.chain().focus().toggleBlockquote().run() },
]

export default function RichEditor({ onChange, uploadImage }) {
  const fileRef = useRef(null)
  const [linkOpen, setLinkOpen] = useState(false)
  const [linkUrl, setLinkUrl] = useState('')
  const [error, setError] = useState('')
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [2, 3] },
        link: { openOnClick: false, autolink: true },
      }),
      Image.configure({ allowBase64: false }),
      Placeholder.configure({ placeholder: '본문을 작성하세요. 이미지도 넣을 수 있습니다.' }),
    ],
    content: '',
    onUpdate: ({ editor: current }) => onChange(current.getHTML()),
    editorProps: { attributes: { class: 'rich-editor-body', 'aria-label': '본문' } },
  })

  const applyLink = () => {
    const href = linkUrl.trim()
    if (!editor) return
    if (!href) editor.chain().focus().unsetLink().run()
    else editor.chain().focus().extendMarkRange('link').setLink({ href }).run()
    setLinkOpen(false)
  }

  const onFile = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || !editor) return
    setError('')
    try {
      const uploaded = await uploadImage(file)
      editor.chain().focus().setImage({ src: uploaded.url }).run()
    } catch (err) {
      setError(err.message || '이미지를 올리지 못했습니다.')
    }
  }

  return (
    <div className="rich-editor">
      <div className="rich-toolbar" role="toolbar" aria-label="서식">
        {TOOLS.map(tool => (
          <button
            key={tool.name}
            type="button"
            className={editor?.isActive(tool.mark) ? 'active' : ''}
            onClick={() => { if (editor) tool.run(editor) }}
          >
            {tool.name}
          </button>
        ))}
        <button type="button" onClick={() => setLinkOpen(open => !open)}>링크</button>
        <button type="button" onClick={() => fileRef.current?.click()}>이미지</button>
        <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/gif,image/webp" hidden onChange={onFile} />
      </div>
      {linkOpen && (
        <div className="rich-link">
          <input
            aria-label="링크 주소"
            value={linkUrl}
            placeholder="https://"
            onChange={(event) => setLinkUrl(event.target.value)}
          />
          <button type="button" onClick={applyLink}>적용</button>
        </div>
      )}
      <EditorContent editor={editor} />
      {error && <p role="alert" className="admin-error" style={{ padding: '0 12px 12px' }}>{error}</p>}
    </div>
  )
}
