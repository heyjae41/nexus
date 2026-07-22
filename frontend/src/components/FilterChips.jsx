/**
 * FilterChips — 목록 상단 필터 알약 버튼 행 (큐레이션·밋플·커뮤니티 공통).
 * options: [{ value, label }], 활성 판정은 value 일치.
 */
export default function FilterChips({ options, value, onChange, ariaLabel, style }) {
  return (
    <div
      role="group"
      aria-label={ariaLabel}
      style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 28, ...style }}
    >
      {options.map(option => {
        const active = value === option.value
        return (
          <button
            key={option.label}
            type="button"
            className="btn chip"
            aria-pressed={active}
            onClick={() => onChange(option.value)}
            style={{
              padding: '8px 16px', borderRadius: 20,
              fontSize: 13, fontWeight: 700,
              background: active ? '#E8123C' : '#15151A',
              color: active ? '#fff' : '#b4b4be',
              border: active ? '1px solid #E8123C' : '1px solid rgba(255,255,255,.08)',
            }}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
