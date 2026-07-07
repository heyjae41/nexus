import '../styles/article.css'

/* Figure A — Dense/Sparse/Balance — §4.3 */
export function FigureA() {
  return (
    <figure style={{ margin: 0 }}>
      <div className="keyvis">
        <div className="figa-dense" />
        <div className="figa-sparse" />
        <div className="figa-scan" />
        <div className="figa-core" />
        <span className="figa-label" style={{ top: 14, left: 14, color: '#B9AEFF' }}>DENSE</span>
        <span className="figa-label" style={{ top: 14, right: 14, color: '#7a7a86' }}>SPARSE</span>
        <span className="figa-label" style={{ bottom: 14, left: '50%', transform: 'translateX(-50%)', color: '#F4788F' }}>BALANCE</span>
      </div>
    </figure>
  )
}

/* Figure B — Stack lanes / HBM — §4.3 */
export function FigureB() {
  const fallDelays = {
    a: ['0s', '.9s', '1.5s'],
    b: ['.4s', '1.2s', '1.8s'],
  }
  return (
    <figure style={{ margin: 0 }}>
      <div className="keyvis" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'center', paddingTop: 20 }}>
        {/* Stack A — green */}
        <div style={{ position: 'relative', marginRight: 70 }}>
          <span className="figb-label" style={{ top: -18, left: '50%', transform: 'translateX(-50%)', whiteSpace: 'nowrap', color: '#4FE3C1' }}>STACK A</span>
          <div className="figb-lane" style={{ background: 'rgba(24,194,156,.22)', position: 'relative' }}>
            {fallDelays.a.map((d, i) => (
              <div key={i} className="figb-dot" style={{
                background: '#4FE3C1',
                boxShadow: '0 0 14px #18C29C',
                animationDelay: d,
              }} />
            ))}
          </div>
        </div>
        {/* Stack B — red */}
        <div style={{ position: 'relative', marginLeft: 70 }}>
          <span className="figb-label" style={{ top: -18, left: '50%', transform: 'translateX(-50%)', whiteSpace: 'nowrap', color: '#F4788F' }}>STACK B</span>
          <div className="figb-lane" style={{ background: 'rgba(232,18,60,.22)', position: 'relative' }}>
            {fallDelays.b.map((d, i) => (
              <div key={i} className="figb-dot" style={{
                background: '#F4788F',
                boxShadow: '0 0 14px #E8123C',
                animationDelay: d,
              }} />
            ))}
          </div>
        </div>
        {/* HBM bar */}
        <div className="figb-bar" />
        <span className="figb-label" style={{ bottom: 8, left: '50%', transform: 'translateX(-50%)', color: '#fff', letterSpacing: '.06em' }}>
          MEMORY · HBM
        </span>
      </div>
    </figure>
  )
}

/* Figure C — Wings — §4.3 */
export function FigureC() {
  return (
    <figure style={{ margin: 0 }}>
      <div className="keyvis">
        <div className="figc-bg" />
        <div style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%,-50%)' }}>
          <div className="figc-wrap">
            <div className="figc-wing figc-wing-l" />
            <div className="figc-wing figc-wing-r" />
            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <div className="figc-core" />
            </div>
          </div>
        </div>
      </div>
    </figure>
  )
}

const FIGURES = { a1: FigureA, a2: FigureB, a3: FigureC }

export default function KeyVisual({ articleId, keyVisualHtml, figCaption }) {
  if (keyVisualHtml) {
    return (
      <figure style={{ margin: 0 }}>
        <div
          className="keyvis"
          dangerouslySetInnerHTML={{ __html: keyVisualHtml }}
        />
        {figCaption && (
          <figcaption style={{
            fontFamily: '"JetBrains Mono", monospace',
            fontSize: 11.5, color: '#6a6a74', marginTop: 8, textAlign: 'center',
          }}>
            {figCaption}
          </figcaption>
        )}
      </figure>
    )
  }

  const Fig = FIGURES[articleId]
  if (!Fig) return null

  return (
    <div>
      <Fig />
      {figCaption && (
        <p style={{
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: 11.5, color: '#6a6a74', marginTop: 8, textAlign: 'center',
        }}>
          {figCaption}
        </p>
      )}
    </div>
  )
}
