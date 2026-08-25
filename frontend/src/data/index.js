/* Static seed data — §3 */

export const CLASSES = [
  { id:'c1', title:'[오프라인] 직장인 AI 개발자 12주 과정', instructor:'EDU.AI LAB', category:'부트캠프', level:'올인원', price:3900000, original:0, chapters:14, hours:14, rating:4.9, students:88, tag:'BEST', desc:'비전공 직장인을 위한 12주 오프라인 부트캠프. 파이썬 기초부터 머신러닝·LLM 활용까지, 퇴근 후 주말 집중 과정으로 현업 AI 개발자로의 전환을 돕습니다. BC카드 현직 멘토링과 팀 프로젝트, 수료 후 사내 연계 채용 추천까지 포함합니다.' },
  { id:'c2', title:'[오프라인] LLM으로 금융 상담 챗봇 만들기', instructor:'이엔지니어', category:'LLM·생성형 AI', level:'중급', price:264000, original:390000, chapters:10, hours:18, rating:4.8, students:870, tag:'NEW', desc:'gemma 27B와 RAG를 활용해 실제 금융 상담 시나리오를 처리하는 챗봇을 처음부터 끝까지 구축합니다.' },
  { id:'c3', title:'[오프라인] 카드 매출 데이터로 배우는 시계열 예측', instructor:'박애널', category:'데이터 분석', level:'중급', price:231000, original:330000, chapters:6, hours:11, rating:4.8, students:540, tag:'', desc:'가맹점 매출 시계열을 다루며 수요 예측 모델을 설계하고, 실제 비즈니스 의사결정에 연결하는 법을 배웁니다.' },
  { id:'c4', title:'[오프라인] 이상거래 탐지(FDS) 모델 만들기', instructor:'정ML', category:'금융 도메인', level:'중급', price:297000, original:420000, chapters:9, hours:16, rating:4.9, students:1580, tag:'BEST', desc:'카드 거래의 이상 패턴을 잡아내는 FDS 모델을, 불균형 데이터 처리부터 실시간 추론까지 실무 그대로 구현합니다.' },
  { id:'c5', title:'[오프라인] RAG로 사내 규정 검색 시스템 구축', instructor:'최RAG', category:'LLM·생성형 AI', level:'중급', price:275000, original:0, chapters:7, hours:13, rating:4.7, students:430, tag:'NEW', desc:'사내 문서를 임베딩하고 벡터 DB로 검색하는 RAG 파이프라인을 구축해, 규정/매뉴얼 Q&A 시스템을 완성합니다.' },
  { id:'c6', title:'[오프라인] 프롬프트 엔지니어링 실무 워크숍', instructor:'한프롬', category:'생산성', level:'입문', price:132000, original:190000, chapters:5, hours:8, rating:4.6, students:2100, tag:'', desc:'업무 자동화에 바로 쓰는 프롬프트 패턴을 익히고, 반복 업무를 LLM으로 처리하는 나만의 템플릿을 만듭니다.' },
  { id:'c7', title:'[오프라인] 개인화 추천 시스템: BC카드 API 활용', instructor:'오레코', category:'금융 도메인', level:'고급', price:330000, original:0, chapters:11, hours:20, rating:4.9, students:320, tag:'NEW', desc:'BC카드 오픈 API와 소비 데이터를 결합해, 사용자별 혜택·가맹점을 추천하는 개인화 엔진을 설계합니다.' },
  { id:'c8', title:'[오프라인] 비전공자를 위한 금융 데이터 리터러시', instructor:'윤기초', category:'커리어', level:'입문', price:99000, original:150000, chapters:6, hours:9, rating:4.7, students:3200, tag:'', desc:'숫자가 두려운 직장인을 위한 입문 과정. 금융 데이터를 읽고 해석하는 감각을 비전공자 눈높이에서 기릅니다.' },
  { id:'c9', title:'[오프라인] 결제 데이터 분석 입문: SQL부터 대시보드까지', instructor:'김데이터', category:'데이터 분석', level:'입문', price:198000, original:290000, chapters:8, hours:14, rating:4.9, students:1240, tag:'', desc:'12주간 주말 집중. BC카드 데이터로 진행하는 팀 프로젝트와 현직 멘토링, 수료 후 사내 연계 채용 추천까지 포함합니다.' },
]

export function getCurriculum(c) {
  if (c.category === 'LLM·생성형 AI') return ['오리엔테이션 & 환경 설정','LLM 기초와 토크나이저','프롬프트 설계 패턴','RAG 파이프라인 이해','벡터 DB & 임베딩','금융 도메인 파인튜닝','평가와 가드레일','배포와 모니터링']
  if (c.category === '금융 도메인') return ['금융 데이터의 특성','피처 엔지니어링','불균형 데이터 다루기','모델 학습과 튜닝','실시간 추론 설계','성능 평가 & 운영']
  return ['데이터 불러오기 & 정제','탐색적 데이터 분석(EDA)','SQL로 집계하기','핵심 지표 설계','시각화 대시보드','인사이트 도출 & 발표']
}

export const CLASS_CATS = ['전체','데이터 분석','LLM·생성형 AI','금융 도메인','생산성','커리어','부트캠프']

export const POSTS = [
  { id:'p1', title:'사내에서 RAG 도입한 후기 (삽질 포함)', author:'데브워커', tag:'노하우', likes:218, time:'2일 전', body:'규정 문서가 수천 페이지라 검색이 지옥이었는데, RAG 붙이고 나서 문의량이 절반으로 줄었습니다. 다만 청킹 전략을 잘못 잡아서 처음엔 엉뚱한 답이 많이 나왔어요. 결국 문서 구조 기반으로 청크를 나누니 정확도가 확 올랐습니다.', commentCount:3 },
  { id:'p2', title:'gemma 27B 로컬 구동 스펙 정리해봤어요', author:'GPU장인', tag:'기술자료', likes:312, time:'4일 전', body:'질문이 많아서 정리합니다. 양자화(4bit) 기준 VRAM 20GB 정도면 무난하게 돌아갑니다. 3090/4090 한 장으로 충분하고, 추론 속도는 토큰당 대략...', commentCount:2 },
  { id:'p3', title:'비전공자도 파인튜닝 해봤습니다', author:'입문러', tag:'노하우', likes:156, time:'5일 전', body:'문과 출신 기획자입니다. EDU.AI LLM 클래스 듣고 처음으로 LoRA 파인튜닝까지 해봤는데, 생각보다 진입장벽이 낮았어요. 데이터셋 만드는 게 제일 오래 걸렸습니다.', commentCount:1 },
  { id:'p4', title:'엑셀 대신 파이썬으로 월말 정산 자동화한 썰', author:'직장인K', tag:'팁', likes:421, time:'1주 전', body:'매달 3일씩 걸리던 정산을 pandas로 자동화했더니 10분이면 끝납니다. 처음엔 무서웠는데 클래스에서 배운 대로 차근차근 하니 됐어요. 코드 공유합니다.', commentCount:2 },
  { id:'p5', title:'프롬프트 템플릿 모음 공유합니다', author:'프롬프트수집가', tag:'자료', likes:689, time:'1주 전', body:'업무별로 자주 쓰는 프롬프트를 정리했습니다. 회의록 요약, 이메일 초안, 데이터 해석 요청 등 바로 복붙해서 쓰세요.', commentCount:1 },
]

export const DEFAULT_COMMENTS = {
  p1:[{a:'러너A',t:'청킹 전략 좀 더 자세히 알 수 있을까요?'},{a:'데브워커',t:'문서 H2 헤딩 단위로 잘랐어요. 곧 글로 정리할게요!'},{a:'호기심',t:'문의량 절반 ㄷㄷ 사내 설득 자료로 써도 될까요'}],
  p2:[{a:'초보',t:'4bit면 품질 손해 많이 보나요?'},{a:'GPU장인',t:'체감상 거의 없습니다. 일반 업무용은 충분해요.'}],
  p4:[{a:'정산러',t:'코드 감사합니다 ㅠㅠ 바로 적용했어요'},{a:'직장인K',t:'도움 됐다니 다행입니다!'}],
}

export function getDefaultComments(id) {
  return DEFAULT_COMMENTS[id] || [{a:'EDU.AI',t:'좋은 글 감사합니다 👏'}]
}

export const EVENTS = [
  { id:'e1', title:'OpenAI Codex 밋업 - 서울', host:'Dev Korea x EDU.AI', date:'2026.07.15 (화)', time:'오후 6:30 – 9:15', location:'MARU180, 강남', going:142, tag:'AI', img:'https://images.lumacdn.com/cdn-cgi/image/format=auto,fit=cover,dpr=1,background=white,quality=75,width=400,height=400/uploads/s3/ddff55c2-c5ba-4d48-8810-54c394bb60f1.png', desc:'OpenAI의 소프트웨어 엔지니어링 에이전트 Codex를 주제로 한 저녁 행사. 최신 업데이트와 라이브 데모, 파워 유저를 위한 실용 팁을 공유합니다. 실시간 통역 제공.', schedule:[['6:30 – 7:00','체크인 & 식사'],['7:00 – 7:05','행사 소개'],['7:05 – 7:40','Valuemaxxing with Codex'],['7:40 – 8:10','세션 #2'],['8:10 – 8:25','커뮤니티 데모'],['8:30 – 9:15','네트워킹']] },
  { id:'e2', title:'EDU.AI 금융 AI 나이트', host:'EDU.AI', date:'2026.07.22 (화)', time:'오후 7:30 – 9:30', location:'BC카드 본사, 을지로', going:88, tag:'금융 AI', img:'https://images.weserv.nl/?url=news.nateimg.co.kr/orgImg/bt/2026/06/29/666808_279461_3154.jpg', desc:'BC카드 데이터로 만든 프로젝트 쇼케이스와 현직자 라이트닝 토크. 수강생 네트워킹 세션이 이어집니다.', schedule:[['7:30 – 8:00','웰컴 & 등록'],['8:00 – 8:40','프로젝트 쇼케이스'],['8:40 – 9:10','라이트닝 토크'],['9:10 – 9:30','네트워킹']] },
  { id:'e3', title:'판교 LLM 스터디 #12', host:'판교AI', date:'2026.07.10 (목)', time:'오후 8:00 – 10:00', location:'판교 스타트업캠퍼스', going:56, tag:'스터디', desc:'매주 진행하는 LLM 논문/실습 스터디. 이번 주제는 효율적 파인튜닝(PEFT)과 LoRA 변형들.', schedule:[['8:00 – 8:10','인트로'],['8:10 – 9:00','논문 리뷰'],['9:00 – 9:50','코드 실습'],['9:50 – 10:00','정리']] },
  { id:'e4', title:'데이터 분석가 커리어 토크', host:'데이터리안', date:'2026.07.18 (금)', time:'오후 7:00 – 8:30', location:'온라인 (Zoom)', going:230, tag:'커리어', desc:'현직 데이터 분석가 3인이 들려주는 직무 전환과 포트폴리오 이야기. Q&A 중심으로 진행됩니다.', schedule:[['7:00 – 7:10','오프닝'],['7:10 – 8:00','패널 토크'],['8:00 – 8:30','라이브 Q&A']] },
  { id:'e5', title:'바이브코딩 해커톤 2026', host:'EDU.AI x Dev Korea', date:'2026.08.02 (토)', time:'오전 10:00 – 오후 8:00', location:'코엑스, 삼성동', going:320, tag:'해커톤', desc:'AI 에이전트와 함께 하루 만에 금융 서비스를 만드는 해커톤. BC카드 API 제공, 우승팀 사내 연계 기회.', schedule:[['10:00','킥오프 & 팀 빌딩'],['11:00','해킹 시작'],['17:00','제출 마감'],['17:30','데모 & 심사'],['19:00','시상 & 네트워킹']] },
]

export const HD_CATS = ['전체','여행','식품/건강','생활/주방','뷰티/헬스','패션/잡화','가전/디지털']

/* Static editorial articles for ArticleDetail rich view — §4.7 */
export const EDITORIAL_ARTICLES = [
  {
    id:'a1', koType:'리서치', section:'AI · 산업 분석',
    title:'앤스로픽의 역설',
    subtitle:'프런티어 벤치마크 1위가, 시장에서 가장 불리한 자리일 수도 있는 이유',
    figCaption:'개념도 — 역량의 밀도: 너무 조밀하거나(dense), 너무 흩어지거나(sparse)',
    author:{ name:'지적 지니', role:'AI 리서처', initial:'지', avatarBg:'linear-gradient(135deg,#7C6BFF,#3A2E8E)', bio:'모델·시장·자본의 교차점을 추적하는 AI 산업 분석 뉴스레터를 씁니다.' },
    date:'2026.07.07', readTime:'4분', rawViews:12840, rawLikes:326,
    tags:['프런티어 모델','시장 구조','에이전트','멀티모달'],
    theme:{
      name:'RESEARCH', chipBg:'rgba(124,107,255,.18)', chipCol:'#B9AEFF',
      heroBase:'radial-gradient(120% 130% at 15% 8%, #2A1E6E 0%, #160E33 40%, #0A0710 74%)',
      blobA:'radial-gradient(circle, rgba(124,107,255,.95), transparent 68%)',
      blobB:'radial-gradient(circle, rgba(232,18,60,.85), transparent 66%)',
      blobC:'radial-gradient(circle, rgba(124,107,255,.6), transparent 70%)',
      ring:'conic-gradient(from 0deg, #7C6BFF, #E8123C, #7C6BFF)',
      relGrad:'linear-gradient(135deg,#7C6BFF,#2A1E6E)', relCol:'#B9AEFF',
    },
    sources:['Artificial Analysis — Intelligence Index','Axios · Ramp — 기업 AI 지출 데이터','Stanford CRFM — Foundation Model 보고서'],
    disclaimer:'',
    blocks:[
      {t:'p',x:'특정 벤치마크에서 1위에 오르는 것과, 시장에서 오래 살아남는 것은 전혀 다른 문제다. 코딩과 장시간 에이전트 작업에서 앞선 한 회사의 우위를 뜯어보면, 그 강점이 오히려 좁은 함정이 될 수 있다는 역설이 드러난다. 지금의 우위 자체는 분명 실재한다. 그러나 그것이 "일상적으로 위임되는 지능"이 아니라 "비싼 순간에만 호출되는 지능"으로 소비된다면, 가장 똑똑해 보이는 회사가 가장 불리한 자리에 설 수도 있다.'},
      {t:'h2',x:'첫 번째 벽 — 가격'},
      {t:'p',x:'최상위 모델의 토큰 단가는 범용 모델의 몇 배에 이른다. 에이전트 작업은 계획·탐색·실패·재시도·검증·도구 호출을 끝없이 반복하며 출력 토큰을 대량으로 태우는 구조다. 이런 환경에서 비싼 모델은 "일을 통째로 맡기는 노동자"가 아니라 "결정적 순간에만 부르는 수석 컨설턴트"가 된다.'},
      {t:'p',x:'그 결과 사용자는 비용을 아끼려 모델을 잘게 쪼갠다. 초안은 싼 모델, 검토만 비싼 모델, 구현은 또 다른 에이전트에 맡기는 라우팅이 자리 잡는다. 고급 지능을 아껴 쓰는 습관은 브랜드를 "좋지만 아껴 써야 하는 도구"로 만든다.'},
      {t:'q',x:'미래의 승자는 가장 똑똑한 모델이 아니라, 사용자가 가장 오래 켜두는 모델일지 모른다.'},
      {t:'h2',x:'두 번째 벽 — 유동적인 시장'},
      {t:'p',x:'B2B는 장기 계약과 높은 단가를 주는 안정적 시장처럼 보인다. 그러나 기업은 특정 브랜드가 아니라 "문제가 풀릴 확률"을 산다. 성능 격차가 조금만 좁혀지거나 가격 대비 성능이 역전되면, 조달팀과 API 라우터는 즉시 더 싼 모델로 갈아탄다.'},
      {t:'h2',x:'세 번째 벽 — 멀티모달 공백'},
      {t:'p',x:'이미지·비디오 생성은 부가 기능이 아니라 공간·물체·시간·물리를 학습하는 별도의 축이다. 역량이 텍스트 추론에만 조밀하게 몰리면, 그 표현을 로보틱스·시뮬레이션·공간 계획으로 전이시키는 통로가 좁아진다.'},
      {t:'call',label:'한눈에 보기',x:'한 회사는 코딩·장기 추론에 너무 조밀(dense)하고, 다른 회사는 조직이 너무 넓게 퍼져(sparse) 있다. 소비자·개발자·코딩·이미지·음성을 고르게 묶은 중간값이 가장 균형 잡힌 포지션을 갖는다.'},
      {t:'def',x:'가장 잘하는 분야로 흥한 회사는, 그 분야만 가장 잘하게 될 위험도 함께 짊어진다.'},
    ],
  },
  {
    id:'a2', koType:'뉴스레터', section:'반도체 · 투자',
    title:'엔비디아 없이 훈련된 AI',
    subtitle:'수출통제의 벽에 생긴 균열, 그리고 자금이 다시 고이는 길목',
    figCaption:'개념도 — 둘로 갈라진 연산 스택이 모두 지나는 길목, 메모리(HBM)',
    author:{ name:'글쓰는 범고래', role:'산업 애널리스트', initial:'범', avatarBg:'linear-gradient(135deg,#18C29C,#0A5647)', bio:'반도체·에너지·자본 흐름을 하나의 지도로 엮는 산업 인사이트를 연재합니다.' },
    date:'2026.07.07', readTime:'4분', rawViews:20310, rawLikes:512,
    tags:['반도체','수출통제','HBM','투자'],
    theme:{
      name:'NEWSLETTER', chipBg:'rgba(24,194,156,.18)', chipCol:'#4FE3C1',
      heroBase:'radial-gradient(120% 130% at 15% 8%, #0C5A49 0%, #08352B 42%, #07120F 76%)',
      blobA:'radial-gradient(circle, rgba(24,194,156,.92), transparent 68%)',
      blobB:'radial-gradient(circle, rgba(232,18,60,.8), transparent 66%)',
      blobC:'radial-gradient(circle, rgba(24,194,156,.55), transparent 70%)',
      ring:'conic-gradient(from 0deg, #18C29C, #E8123C, #18C29C)',
      relGrad:'linear-gradient(135deg,#18C29C,#0A5647)', relCol:'#4FE3C1',
    },
    sources:['메이투안 LongCat 모델 카드 및 공개 발표 (2026.6)','모건스탠리 — 중국 AI 칩 성능 비교','골드만삭스 · 번스타인 — 시장 영향 분석'],
    disclaimer:'이 글은 특정 종목의 매수·매도를 권유하지 않으며, 투자 판단과 책임은 전적으로 투자자 본인에게 있습니다.',
    blocks:[
      {t:'call',label:'3줄 요약',x:'한 중국 대형 IT 기업이 조(兆) 단위 파라미터 모델을 전량 국산 칩으로 사전학습까지 완주했다. "훈련은 결국 엔비디아여야 한다"는 수출통제의 전제에 금이 갔다. 스택이 둘로 갈라질수록 두 갈래가 모두 반드시 지나는 메모리라는 길목의 전략적 가치는 오히려 올라간다.'},
      {t:'h2',x:'무슨 일이 있었나'},
      {t:'p',x:'AI 모델은 사전학습·사후학습·추론의 세 단계로 만들어진다. 그동안 중국의 국산 칩은 가벼운 추론에서만 쓰였고, 무거운 사전학습만큼은 엔비디아 하드웨어에 기대야 했다. 이번 모델은 그 가장 무거운 단계를 처음부터 끝까지 국산 하드웨어 위에서 돌렸다.'},
      {t:'p',x:'이것은 단순한 하드웨어 소식이 아니다. 그 위에서 대형 모델을 안정적으로 훈련시키는 "운영 능력"까지 확보했다는 뜻이기 때문이다.'},
      {t:'h2',x:'이건 "모델"이 아니라 "벽"의 이야기다'},
      {t:'p',x:'수출통제의 급소는 "훈련이라는 문턱"이었다. 국가대표급 기업뿐 아니라 생활 서비스 기업까지 프런티어 규모의 사전학습을 해냈다는 건, 그 능력이 특정 소수에 갇혀 있지 않다는 신호로 읽힌다.'},
      {t:'q',x:'"누가 엔비디아를 이겼다"가 아니라, "엔비디아 독점이 영원할 것"이라는 가정에 금이 갔다.'},
      {t:'h2',x:'두 개의 스택, 그리고 남은 격차'},
      {t:'p',x:'그렇다고 격차가 사라진 건 아니다. 국산 가속기는 메모리가 부족해 사전학습의 병목이 되고, 소프트웨어 생태계는 여전히 뒤진다. 훈련의 문턱은 넘었지만, 효율의 격차는 아직 열린 질문이다.'},
      {t:'h2',x:'그래서 돈은 어디로 흐르는가'},
      {t:'p',x:'스택이 미국식이든 중국식이든, 대형 모델을 훈련하려면 고대역폭 메모리(HBM)가 반드시 필요하다. 어느 쪽이 이기든 그 아래에서 메모리를 대는 층의 수요는 끊기지 않는다.'},
      {t:'ul',items:['연산 칩 — 표준은 여전하지만, 처음으로 "열등하지만 작동하는 대안"이 등장했다','공통 병목 — 메모리·패키징·파운드리, 어느 시나리오에서도 붐비는 가장 단단한 자리','소프트웨어 생태계 — CUDA라는 진짜 해자이자, 가장 넘기 어려운 마지막 벽']},
      {t:'def',x:'세계의 연산이 둘로 갈라질 때, 돈은 승자의 칩이 아니라 두 갈래가 모두 지나는 길목에 고인다.'},
    ],
  },
  {
    id:'a3', koType:'칼럼', section:'오피니언 · 시니어',
    title:'시니어에게 AI는 날개가 된다',
    subtitle:'AI를 이기려는 적이 아니라, 곁에서 돕는 동료로 두는 법',
    figCaption:'개념도 — 두려움을 내려놓으면, 도구는 등에 날개가 된다',
    author:{ name:'박근필', role:'칼럼니스트 · 수의사', initial:'박', avatarBg:'linear-gradient(135deg,#FF9F43,#8A4A0A)', bio:'나이 듦과 배움, 그리고 기술과 사람 사이의 태도에 관해 씁니다.' },
    date:'2026.06.16', readTime:'4분', rawViews:8420, rawLikes:289,
    tags:['시니어','AI 활용','디지털 문해','태도'],
    theme:{
      name:'COLUMN', chipBg:'rgba(255,159,67,.2)', chipCol:'#FFC07A',
      heroBase:'radial-gradient(120% 130% at 15% 8%, #7A3B0A 0%, #3E1E06 44%, #120A05 78%)',
      blobA:'radial-gradient(circle, rgba(255,159,67,.9), transparent 68%)',
      blobB:'radial-gradient(circle, rgba(232,18,60,.8), transparent 66%)',
      blobC:'radial-gradient(circle, rgba(255,159,67,.55), transparent 70%)',
      ring:'conic-gradient(from 0deg, #FF9F43, #E8123C, #FF9F43)',
      relGrad:'linear-gradient(135deg,#FF9F43,#8A4A0A)', relCol:'#FFC07A',
    },
    sources:[],
    disclaimer:'',
    blocks:[
      {t:'p',x:'"그건 젊은 사람들이나 하는 거지." AI라는 말만 들어도 손사래부터 치는 분들이 많다. 그러나 가만히 들여다보면 그 두려움의 정체는 대개 하나다 — 한 번도 해본 적이 없다는 것. 낯섦이 두려움으로 둔갑했을 뿐이다.'},
      {t:'p',x:'AI 앞에서 정말 중요한 건 나이가 아니라 태도다. 예순이든 일흔이든 새로운 걸 받아들이려는 마음만 있으면 된다. 얼마 전에는 여든이 넘은 한 어른이 인공지능으로 손수 만든 캐릭터를 선물로 보내오셨다. 나이는 정말 숫자에 불과했다.'},
      {t:'q',x:'걸어서 가야 했던 길을, 이제는 날아서 갈 수 있다.'},
      {t:'h2',x:'어떻게 쓰면 될까'},
      {t:'p',x:'거창하게 생각할 것 없다. 어떤 이는 AI를 "무한한 기억력을 가진 똑똑한 컨설턴트"에 비유한다. 지치지도, 짜증 내지도 않고 곁에서 나를 돕는 비서다. 이렇게 작게 시작하면 된다.'},
      {t:'ul',items:['모르는 단어의 뜻, 병원에서 들은 어려운 설명을 쉽게 풀어 달라 하기','손주에게 줄 편지를 다정하게 다듬어 달라 하기','오늘 본 영화의 줄거리와 감상을 정리해 달라 하기']},
      {t:'p',x:'배우는 길도 멀지 않다. "내가 인공지능이 서툴러. 너를 잘 쓰는 법을 쉽게 알려줘." 이렇게 물으면 누구보다 친절하고 상세하게 알려준다. 하루 30분이면 충분하다.'},
      {t:'call',label:'딱 하나만 기억하세요',x:'AI는 모르는 것도 아는 척 그럴듯하게 지어낸다(할루시네이션). 그래서 마지막 검증과 판단은 늘 사람의 몫이다. 살아오며 쌓은 경험과 분별력 — 그건 세월이 준 선물이다.'},
      {t:'def',x:'AI는 우리를 이기려는 적이 아니라, 두려움만 내려놓으면 등에 날개가 되어 주는 동료다.'},
    ],
  },
]
