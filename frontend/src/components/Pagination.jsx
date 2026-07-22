/** 목록 하단 페이지 버튼 — totalPages 1 이하면 렌더링하지 않는다. */
export default function Pagination({ totalPages, page, onPage, ariaLabel }) {
  if (totalPages <= 1) return null
  return (
    <nav
      aria-label={ariaLabel}
      style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 40 }}
    >
      {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
        <button
          key={p}
          className="btn"
          aria-current={p === page ? 'page' : undefined}
          onClick={() => onPage(p)}
          style={{
            width: 36, height: 36, borderRadius: 8,
            fontSize: 14, fontWeight: 600,
            background: p === page ? '#E8123C' : 'rgba(255,255,255,.06)',
            color: p === page ? '#fff' : '#9a9aa4',
            border: 'none',
          }}
        >
          {p}
        </button>
      ))}
    </nav>
  )
}
