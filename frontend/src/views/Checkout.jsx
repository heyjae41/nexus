import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { CLASSES } from '../data'
import { classGrad, fmtKo } from '../utils/grads'

export default function Checkout({ onPay }) {
  const { classId } = useParams()
  const navigate = useNavigate()
  const cls = CLASSES.find(c => c.id === classId)
  const [payDone, setPayDone] = useState(false)
  const [installment, setInstallment] = useState('일시불')

  if (!cls) {
    return (
      <main style={{ padding: '64px 40px', maxWidth: 480, margin: '0 auto', textAlign: 'center' }}>
        <p style={{ fontSize: 16, color: '#9a9aa4', marginBottom: 24 }}>클래스를 찾을 수 없습니다.</p>
        <button
          className="btn"
          onClick={() => navigate('/classes')}
          style={{
            background: '#E8123C', color: '#fff',
            fontSize: 14, fontWeight: 700, padding: '10px 22px', borderRadius: 10,
          }}
        >
          ← 클래스 목록
        </button>
      </main>
    )
  }

  const price = cls.price
  const discount = Math.floor(price * 0.05)
  const final = price - discount

  const grad = classGrad(CLASSES.indexOf(cls))

  const doPay = () => {
    setPayDone(true)
    onPay?.('김크레딧')
  }

  if (payDone) {
    return (
      <main style={{ padding: '64px 40px', maxWidth: 480, margin: '0 auto', textAlign: 'center' }}>
        <div style={{
          width: 74, height: 74, borderRadius: '50%',
          background: '#1F8A5B',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 32, margin: '0 auto 24px',
        }}>
          ✓
        </div>
        <h1 style={{ fontSize: 26, fontWeight: 800, color: '#fff', margin: '0 0 12px' }}>수강 신청 완료!</h1>
        <p style={{ fontSize: 15, color: '#9a9aa4', margin: '0 0 32px' }}>
          비씨카드로 결제가 완료되었어요. 지금 바로 학습을 시작해보세요.
        </p>
        <button className="btn" onClick={() => navigate('/dashboard')} style={{
          width: '100%', background: '#E8123C', color: '#fff',
          fontSize: 15, fontWeight: 700, padding: '13px 0', borderRadius: 12, marginBottom: 12,
        }}>
          내 학습 대시보드로
        </button>
        <button className="btn ghost" onClick={() => navigate('/classes')} style={{
          width: '100%', background: 'transparent', color: '#dcdce2',
          fontSize: 14, fontWeight: 600, padding: '12px 0', borderRadius: 12,
          border: '1px solid rgba(255,255,255,.14)',
        }}>
          다른 클래스 보기
        </button>
      </main>
    )
  }

  return (
    <main style={{ padding: '32px 40px 64px', maxWidth: 920, margin: '0 auto' }}>
      <div className="detailgrid detailgrid-checkout" style={{ gap: 32 }}>
        {/* Left */}
        <div>
          <button className="back-link btn" onClick={() => navigate(`/classes/${cls.id}`)}
            style={{ background: 'none', border: 'none', color: '#8a8a94', fontSize: 13.5, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, padding: '0 0 20px' }}>
            ← 클래스
          </button>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: '#fff', margin: '0 0 24px' }}>결제하기</h1>

          <p style={{ fontSize: 15, fontWeight: 700, color: '#ECECEF', margin: '0 0 14px' }}>결제 수단</p>

          {/* BC Card UI */}
          <div style={{
            background: 'linear-gradient(120deg,#E8123C,#8A0A22)',
            borderRadius: 16, padding: '22px 24px', marginBottom: 12,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 18 }}>
              <span style={{ fontSize: 16, fontWeight: 800, color: '#fff' }}>BC카드</span>
              <span style={{ fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,.7)', letterSpacing: '.06em' }}>PRIMARY</span>
            </div>
            <p style={{
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: 14, color: 'rgba(255,255,255,.9)', margin: '0 0 18px', letterSpacing: '.1em',
            }}>
              5409 •••• •••• 2026
            </p>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
              <span style={{ fontSize: 12.5, color: 'rgba(255,255,255,.8)', fontWeight: 600 }}>KIM CREDIT</span>
              <span style={{ fontSize: 11, color: 'rgba(255,255,255,.7)', letterSpacing: '.03em' }}>구독 5% 청구할인 적용</span>
            </div>
          </div>

          <div style={{
            border: '1px dashed rgba(255,255,255,.18)',
            borderRadius: 20, padding: '10px 18px',
            fontSize: 14, color: '#7a7a84', cursor: 'pointer',
            marginBottom: 24, textAlign: 'center',
          }}>
            + 다른 카드로 결제
          </div>

          <p style={{ fontSize: 14, fontWeight: 600, color: '#9a9aa4', margin: '0 0 12px' }}>할부 개월</p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {['일시불', '3개월', '6개월', '12개월'].map(m => (
              <button key={m} className="btn chip" onClick={() => setInstallment(m)} style={{
                padding: '8px 16px', borderRadius: 20, fontSize: 13.5, fontWeight: 600,
                background: installment === m ? '#E8123C' : '#15151A',
                color: installment === m ? '#fff' : '#b4b4be',
                border: installment === m ? '1px solid #E8123C' : '1px solid rgba(255,255,255,.12)',
              }}>
                {m}
              </button>
            ))}
          </div>
        </div>

        {/* Right — sticky summary */}
        <div className="sticky-box">
          <div style={{
            background: '#15151A', border: '1px solid rgba(255,255,255,.10)',
            borderRadius: 18, padding: '22px',
          }}>
            {/* Thumbnail + title */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 18, alignItems: 'center' }}>
              <div style={{ width: 60, height: 40, borderRadius: 8, background: grad, flexShrink: 0 }} />
              <p style={{ fontSize: 13.5, fontWeight: 700, color: '#ECECEF', margin: 0, lineHeight: 1.4 }}>
                {cls.title}
              </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, paddingBottom: 16, borderBottom: '1px solid rgba(255,255,255,.08)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 14, color: '#9a9aa4' }}>강의 금액</span>
                <span style={{ fontSize: 14, color: '#ECECEF' }}>{fmtKo(price)}원</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 14, color: '#9a9aa4' }}>비씨카드 할인</span>
                <span style={{ fontSize: 14, color: '#1F8A5B', fontWeight: 600 }}>-5%</span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', margin: '16px 0 20px' }}>
              <span style={{ fontSize: 15, fontWeight: 700, color: '#fff' }}>최종 결제금액</span>
              <span style={{ fontSize: 24, fontWeight: 800, color: '#fff' }}>{fmtKo(final)}원</span>
            </div>

            <button className="btn" onClick={doPay} style={{
              width: '100%', background: '#E8123C', color: '#fff',
              fontSize: 15, fontWeight: 700, padding: '13px 0', borderRadius: 12, marginBottom: 12,
            }}>
              {fmtKo(final)}원 결제하기
            </button>
            <p style={{ fontSize: 11.5, color: '#55555f', textAlign: 'center', margin: 0 }}>
              결제 시 이용약관 및 개인정보처리방침에 동의합니다.
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}
