/**
 * MeetDetail — 참가 신청은 브라우저 dialog(alert) 대신 인라인 UI 로 피드백한다.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import MeetDetail from '@/views/MeetDetail'

const wrap = () => render(
  <MemoryRouter initialEntries={['/meet/e1']}>
    <Routes>
      <Route path="/meet/:id" element={<MeetDetail />} />
    </Routes>
  </MemoryRouter>,
)

describe('MeetDetail 참가 신청', () => {
  afterEach(() => vi.restoreAllMocks())

  it('신청 시 alert 없이 인라인 완료 메시지를 보여주고 중복 신청을 막는다', async () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    const ue = userEvent.setup()
    wrap()

    await ue.click(screen.getByRole('button', { name: '참가 신청하기' }))

    expect(alertSpy).not.toHaveBeenCalled()
    expect(screen.getByRole('status')).toHaveTextContent('참가 신청이 완료되었습니다')
    expect(screen.getByRole('button', { name: /신청 완료/ })).toBeDisabled()
  })
})
