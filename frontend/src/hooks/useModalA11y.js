import { useEffect } from 'react'

/**
 * 모달/오버레이 공통 접근성 — Esc 닫기 + Tab 포커스 트랩 + 배경 스크롤 잠금 +
 * 닫힐 때 열었던 요소로 포커스 복원 (Nav 모바일 메뉴·AuthModal 공유).
 */
export function useModalA11y({
  active,
  containerRef,
  onClose,
  initialFocusRef,
  focusableSelector = 'a[href], input, button:not([disabled])',
}) {
  useEffect(() => {
    if (!active) return undefined
    const trigger = document.activeElement
    const handleKeyboard = (event) => {
      if (event.key === 'Escape') {
        onClose()
        return
      }
      if (event.key !== 'Tab') return
      const focusable = [...(containerRef.current?.querySelectorAll(focusableSelector) ?? [])]
      if (!focusable.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', handleKeyboard)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    initialFocusRef?.current?.focus()
    return () => {
      document.removeEventListener('keydown', handleKeyboard)
      document.body.style.overflow = previousOverflow
      if (trigger?.isConnected) trigger.focus()
    }
    // containerRef/initialFocusRef 는 ref 라 의존성에서 제외한다
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, onClose, focusableSelector])
}
