// GA 부트스트랩 — index.html 인라인이 아니라 정적 파일로 두는 이유:
// docker/security-headers.conf 의 CSP(script-src 'self')가 인라인 스크립트를 막는다.

// 로컬 개발·자동화(vite dev, Playwright) 트래픽이 운영 GA 속성을 오염시키지
// 않도록 공식 opt-out 플래그로 차단한다 — 실서비스 호스트에서만 수집.
if (['localhost', '127.0.0.1'].includes(window.location.hostname)) {
  window['ga-disable-G-YCKV0L1G97'] = true;
}
window.dataLayer = window.dataLayer || [];
function gtag() { dataLayer.push(arguments); }
gtag('js', new Date());

// page_view 는 라우터 훅(usePageTitle)이 제목 설정 직후 수동 전송한다 —
// 자동 전송은 SPA 전환 시 이전 페이지 제목이 붙는 문제(off-by-one)가 있다.
gtag('config', 'G-YCKV0L1G97', { send_page_view: false });
