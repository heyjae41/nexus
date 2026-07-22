/* 목록 뷰 공통 에러·빈 상태 표시 */

export function ErrorRetry({ message, onRetry, retryLabel = '다시 시도' }) {
  return (
    <div className="empty-state">
      <p style={{ marginBottom: 12 }}>{message}</p>
      <button
        className="btn"
        onClick={onRetry}
        style={{
          background: '#E8123C', color: '#fff',
          padding: '10px 20px', borderRadius: 10, fontSize: 14, fontWeight: 700,
        }}
      >
        {retryLabel}
      </button>
    </div>
  )
}

export function EmptyMessage({ children }) {
  return (
    <div className="empty-state">
      <p>{children}</p>
    </div>
  )
}
