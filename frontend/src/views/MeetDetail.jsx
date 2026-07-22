import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { EVENTS } from '../data'
import { meetGrad, fmtKo } from '../utils/grads'

export default function MeetDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [applied, setApplied] = useState(false)
  const event = EVENTS.find(e => e.id === id)
  if (!event) return <div style={{ padding: 40, color: '#9a9aa4' }}>이벤트를 찾을 수 없습니다.</div>

  const index = EVENTS.indexOf(event)
  const grad = meetGrad(index)
  const coverBg = event.img
    ? `center/cover no-repeat url(${event.img}), ${grad}`
    : grad

  return (
    <main style={{ padding: '32px 40px 64px', maxWidth: 980, margin: '0 auto' }}>
      <div className="detailgrid detailgrid-meet">
        {/* Left — cover + host */}
        <div>
          <div style={{
            aspectRatio: '1/1', borderRadius: 18, overflow: 'hidden',
            background: coverBg, marginBottom: 16,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {!event.img && (
              <p style={{ fontSize: 18, fontWeight: 700, color: 'rgba(255,255,255,.7)', textAlign: 'center', padding: 20 }}>
                {event.title}
              </p>
            )}
          </div>
          <div style={{
            background: '#15151A', border: '1px solid rgba(255,255,255,.07)',
            borderRadius: 14, padding: '14px 16px',
          }}>
            <p style={{ fontSize: 11.5, color: '#7a7a84', margin: '0 0 6px', fontWeight: 600 }}>호스트</p>
            <p style={{ fontSize: 15, fontWeight: 700, color: '#ECECEF', margin: 0 }}>{event.host}</p>
          </div>
        </div>

        {/* Right — details */}
        <div>
          <button
            className="back-link btn"
            onClick={() => navigate('/meet')}
            style={{ background: 'none', border: 'none', color: '#8a8a94', fontSize: 13.5, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, padding: '0 0 18px' }}
          >
            ← meet.pl
          </button>
          <h1 style={{ fontSize: 30, fontWeight: 800, color: '#fff', lineHeight: 1.25, letterSpacing: '-.025em', margin: '0 0 20px' }}>
            {event.title}
          </h1>

          {/* Date box */}
          <div style={{
            background: '#13131A', border: '1px solid rgba(255,255,255,.07)',
            borderRadius: 14, padding: '14px 18px',
            display: 'flex', alignItems: 'center', gap: 14, marginBottom: 12,
          }}>
            <div style={{
              width: 46, height: 46, borderRadius: 10, flexShrink: 0,
              background: '#1d1d24', display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: 10, fontWeight: 600, color: '#E8123C', letterSpacing: '.04em',
            }}>
              DATE
            </div>
            <div>
              <p style={{ fontSize: 14.5, fontWeight: 700, color: '#ECECEF', margin: '0 0 2px' }}>{event.date}</p>
              <p style={{ fontSize: 13.5, color: '#9a9aa4', margin: 0 }}>{event.time}</p>
            </div>
          </div>

          {/* Location */}
          <div style={{
            background: '#13131A', border: '1px solid rgba(255,255,255,.07)',
            borderRadius: 14, padding: '14px 18px',
            display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20,
          }}>
            <span style={{ fontSize: 18 }}>📍</span>
            <div>
              <p style={{ fontSize: 14.5, fontWeight: 700, color: '#ECECEF', margin: '0 0 2px' }}>{event.location}</p>
              <p style={{ fontSize: 13, color: '#7a7a84', margin: 0 }}>{fmtKo(event.going)}명 참여 예정</p>
            </div>
          </div>

          <button
            className="btn"
            disabled={applied}
            onClick={() => setApplied(true)}
            style={{
              width: '100%', background: applied ? '#2a2a31' : '#E8123C', color: '#fff',
              fontSize: 15, fontWeight: 700, padding: '13px 0',
              borderRadius: 12, marginBottom: applied ? 10 : 24,
              cursor: applied ? 'default' : 'pointer',
            }}
          >
            {applied ? '✓ 신청 완료' : '참가 신청하기'}
          </button>
          {applied && (
            <p role="status" style={{
              fontSize: 13.5, color: '#4FE3C1', margin: '0 0 24px',
              textAlign: 'center',
            }}>
              참가 신청이 완료되었습니다!
            </p>
          )}

          {/* Description */}
          <p style={{ fontSize: 15.5, lineHeight: 1.8, color: '#b4b4be', margin: '0 0 28px' }}>
            {event.desc}
          </p>

          {/* Timeline */}
          {event.schedule?.length > 0 && (
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 800, color: '#fff', margin: '0 0 16px' }}>진행 순서</h2>
              <div style={{ paddingLeft: 16, borderLeft: '2px solid rgba(232,18,60,.4)' }}>
                {event.schedule.map(([time, item], i) => (
                  <div key={i} style={{
                    display: 'flex', gap: 16, alignItems: 'flex-start',
                    marginBottom: i < event.schedule.length - 1 ? 16 : 0,
                  }}>
                    <span style={{
                      fontFamily: '"JetBrains Mono", monospace',
                      fontSize: 12, fontWeight: 600, color: '#E8123C',
                      minWidth: 96, flexShrink: 0,
                    }}>
                      {time}
                    </span>
                    <span style={{ fontSize: 14.5, color: '#dcdce2', lineHeight: 1.5 }}>{item}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  )
}
