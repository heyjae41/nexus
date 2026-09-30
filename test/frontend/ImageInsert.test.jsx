import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RichEditor from '@/components/RichEditor'
import { hasUnstoredImage } from '@/views/admin/articleImages'
describe('image insert', () => {
  it('uploads and puts the server url in the html', async () => {
    const htmls = []
    const uploadImage = async () => ({ url: '/api/media/authored/shot.png' })
    render(<RichEditor onChange={(html) => htmls.push(html)} uploadImage={uploadImage} />)
    const input = document.querySelector('input[type="file"]')
    const file = new File([new Uint8Array([137, 80, 78, 71])], 'shot.png', { type: 'image/png' })
    await userEvent.upload(input, file)
    await waitFor(() => {
      expect(htmls.some(html => html.includes('/api/media/authored/shot.png'))).toBe(true)
    })
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})

describe('저장된 이미지 주소', () => {
  it('서버 미디어 주소만 글에 남길 수 있다', () => {
    expect(hasUnstoredImage('<p>글</p><img src="https://cdn.example/a.png" alt="외부">')).toBe(true)
    expect(hasUnstoredImage('<img src="/api/media/authored/a.png">')).toBe(false)
    expect(hasUnstoredImage('<img src="https://edu.dev.bccard.ai/api/media/authored/a.png">')).toBe(false)
    expect(hasUnstoredImage('<p>글만</p>')).toBe(false)
  })
})
