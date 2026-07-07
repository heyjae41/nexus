/**
 * PageLabel — the small JetBrains Mono category label shown above page headings.
 * Usage: <PageLabel>CLASS · 데이터사이언스 / AI</PageLabel>
 */
export default function PageLabel({ children }) {
  return (
    <p style={{
      fontFamily: '"JetBrains Mono", monospace',
      fontSize: 11, fontWeight: 600, letterSpacing: '.06em',
      color: '#E8123C', margin: '0 0 10px',
    }}>
      {children}
    </p>
  )
}
