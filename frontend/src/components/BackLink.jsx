import { useNavigate } from 'react-router-dom'

/** 상세/작성 페이지 상단 "← 목록" 텍스트 버튼 */
export default function BackLink({ to, children, bottomGap = 20 }) {
  const navigate = useNavigate()
  return (
    <button
      className="back-link btn"
      onClick={() => navigate(to)}
      style={{
        background: 'none', border: 'none', color: '#8a8a94',
        fontSize: 13.5, cursor: 'pointer',
        display: 'flex', alignItems: 'center', gap: 6,
        padding: `0 0 ${bottomGap}px`,
      }}
    >
      {children}
    </button>
  )
}
