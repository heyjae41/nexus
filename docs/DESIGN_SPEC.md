# NEXUS 디자인 명세서 (Implementation-Grade Design Spec)

> BC카드 AI 사업팀의 금융 AI 학습 채널 "NEXUS" 프런트엔드 재구축용 명세.
> 이 문서 하나만으로 원본 소스를 보지 않고 UI를 충실히 재현할 수 있도록 작성되었다.
> 슬로건: "금융과 AI, 일하면서 배웁니다." / "퇴근 후 30분, 금융 AI 한 스푼."

- **컨셉**: 다크 테마 SPA. 강렬한 레드(BC카드/NEXUS 브랜드) 액센트 + 그라디언트 카드 썸네일.
- **폰트**: Pretendard (본문/UI), JetBrains Mono (라벨/코드/뱃지, `.mono` 클래스).
- **전역 배경**: `#08080B` (거의 검정).
- **전역 텍스트**: `#ECECEF`.
- **폰트 스무딩**: `-webkit-font-smoothing:antialiased`.
- 두 개의 SPA 앱이 있음: (1) **홈 앱** (라우트 상태 머신 기반 멀티뷰), (2) **아티클 상세 앱** (독립 페이지, 애니메이션 키비주얼 + 읽기 진행바).

---

## 1. 디자인 토큰

### 1.1 색상 (Colors)

#### 배경 (Background) 계층
| 역할 | HEX | 용도 |
|---|---|---|
| 앱 최상위 배경 | `#08080B` | body, 전체 SPA 래퍼 (`min-height:100vh`) |
| 핫딜 페이지 배경 | `#0A0A12` | AI핫딜 뷰 전용 (약간 푸른 검정) |
| 서피스 (카드) | `#15151A` | 기본 카드/패널 배경 (거의 모든 카드) |
| 서피스 (진한) | `#13131A` | 커리큘럼 행, 밋플 정보 박스, 대시보드 빈 상태, 아티클 상세 카드 |
| 서피스 (아티클) | `#131318` | 아티클 상세의 callout/저자 카드 |
| 서피스 (핫딜 카드) | `#12121C` | 핫딜 상품 카드 |
| 키비주얼 배경 | `#0B0B10` | 아티클 상세 키비주얼 컨테이너 |
| 푸터 밴드 | `#0C0C10` | 홈 하단 푸터 |
| 클래스 상세 배너 | `#0E0E13` | 클래스 상세 상단 배너 |
| 스크롤바 트랙 | `#0e0e12` | |
| 스크롤바 썸 | `#26262e` | 프로그레스바 트랙, 아바타 원 배경으로도 사용 |
| 온보딩 프로그레스 미완료 | `#26262e` | |
| 밋플 아이콘칩 배경 | `#1d1d24` | 날짜/장소 아이콘 박스 |
| 카테고리 칩 비활성 | `#15151A` | |
| 헤더 배경 | `rgba(8,8,11,.82)` + `backdrop-filter:blur(14px)` | 스티키 상단바 |
| 모바일 하단 네비 배경 | `rgba(10,10,14,.96)` + `blur(14px)` | |

#### 액센트 (Accent) — 브랜드 레드
| 역할 | HEX | 용도 |
|---|---|---|
| 프라이머리 레드 | `#E8123C` | 브랜드 로고 점, 활성 네비, CTA 버튼, 카테고리 라벨, 진행바, 강조 라인, 활성 칩 |
| 레드 (밝은/핑크) | `#F4788F` | 좋아요 활성 텍스트, "한 줄 정의" 라벨, 아티클 링크(`a`) |
| 레드 (진한) | `#7A0A22` / `#8A0A22` | 그라디언트 짝, 아바타 그라디언트 |
| 레드 진행바 그라디언트 | `linear-gradient(90deg,#E8123C,#FF5A7A)` | 읽기 진행바 |
| 핫딜 액센트 (블루-보라) | `#3E3FD9` (칩), `#6E6FF5` (라벨/카테고리) | 핫딜 뷰의 액센트 (레드 대신 블루 계열) |
| 성공/할인 그린 | `#1F8A5B` | 결제 완료 원, 비씨카드 할인 `-5%` 텍스트 |
| CTA 버튼 배경 | `#fff` (흰색, 텍스트는 `#E8123C`) | 헤더 시작하기 버튼, 히어로 CTA |

레드 반투명 변형: `rgba(232,18,60,.12)` (커뮤니티 태그칩 배경), `rgba(232,18,60,.14)~.16` (좋아요/정의 배경), `rgba(232,18,60,.35~.5)` (테두리), `rgba(232,18,60,.4)` (밋플 타임라인 선).

#### 텍스트 (Text) 계층
| 역할 | HEX | 용도 |
|---|---|---|
| 최상위 (제목/흰색) | `#fff` | h1, 큰 제목, 가격, 버튼 텍스트 |
| 헤딩 밝은 | `#F5F5F7` | 홈 섹션 h2, 인용문 |
| 본문 강조 | `#ECECEF` | 카드 타이틀, 기본 body |
| 본문 (밝은 회색) | `#dcdce2` | 커리큘럼 텍스트, 부제, ghost 버튼 텍스트 |
| 본문 (중간) | `#d3d3db` / `#d2d2da` | callout 본문, 로그인 라벨 |
| 본문 프로즈 | `#cacad2` / `#c8c8d0` / `#c9c9d2` | 아티클/글 본문 (긴 텍스트) |
| 서브 텍스트 | `#b4b4be` / `#b6b6c0` | 설명문, 댓글 본문, 비활성 칩 텍스트 |
| 보조 텍스트 | `#9a9aa4` | 부제/설명, 메타 정보 |
| 흐린 메타 | `#8a8a94` | 뒤로가기 링크, 날짜, 저자 역할 |
| 더 흐린 메타 | `#7a7a84` | 카드 하단 메타 (저자·시간·좋아요) |
| 플레이스홀더/아이콘 | `#6a6a74` | 검색창 텍스트, figcaption, mono 메타 |
| 비활성 네비 | `#a6a6b0` | 상단 네비 비활성 링크 |
| 가장 흐림 | `#666` / `#55555f` / `#5a5a64` | 취소선 원가, 각주, 데이터 출처 |
| 화살표(비활성) | `#3a3a42` | 커리큘럼 ▶ 아이콘 |

#### 테두리 (Borders)
| 역할 | 값 |
|---|---|
| 기본 카드 테두리 | `1px solid rgba(255,255,255,.06)` |
| 서피스 테두리 (약간 진함) | `1px solid rgba(255,255,255,.07)` ~ `.08` |
| 패널/구매박스 테두리 | `1px solid rgba(255,255,255,.1)` |
| 입력창 테두리 | `1px solid rgba(255,255,255,.12)` |
| 칩/pill 테두리 | `1px solid rgba(255,255,255,.14)` ~ `.16` ~ `.18` |
| 헤더 하단 구분선 | `1px solid rgba(255,255,255,.07)` |
| 섹션 구분선 | `1px solid rgba(255,255,255,.08)` |
| 점선 (다른카드/빈상태) | `1px dashed rgba(255,255,255,.14~.18)` |
| 카드 호버 테두리 | `rgba(232,18,60,.5)` (레드) |
| 밋플 타임라인 좌측선 | `2px solid rgba(232,18,60,.4)` |
| 아티클 인용문 좌측선 | `3px solid #E8123C` |
| h2 액센트 바 | `width:5px;height:22px;border-radius:3px;background:#E8123C` |

#### 그림자 (Shadows)
- 플로팅 유형 스위처 (아티클): `box-shadow:0 12px 40px rgba(0,0,0,.5)`.
- 키비주얼 애니메이션 요소 발광: `box-shadow:0 0 14px~40px` (테마 색상).
- 카드에는 기본 그림자 없음 (테두리 + hover translateY로 입체감 표현).

### 1.2 타이포그래피 (Typography)

폰트 패밀리: `"Pretendard", system-ui, sans-serif` (본문/전체), `"JetBrains Mono", monospace` (`.mono` — 라벨·뱃지·코드·날짜·카테고리 태그).

| 요소 | size | weight | line-height | letter-spacing | color |
|---|---|---|---|---|---|
| 로고 "NEXUS" | 21px (온보딩 20px) | 800 | — | -.03em | #fff |
| 홈 히어로 h1 | 52px (모바일 34px) | 800 | 1.1 | -.04em | #fff |
| 페이지 h1 (목록) | 32px | 800 | — | -.03em | #fff |
| 클래스 상세 h1 | 30px | 800 | 1.25 | -.025em | #fff |
| 아티클 상세 h1 (히어로) | 46px (모바일 33/27px) | 800 | 1.18 | -.035em | #fff |
| 큐레이션 상세 h1 | 34px | 800 | 1.3 | -.025em | #fff |
| 커뮤니티 상세 h1 | 26px | 800 | 1.35 | -.02em | #fff |
| 온보딩/결제 h1 | 26px | 800 | — | -.02em | #fff |
| 섹션 h2 (홈) | 23px | 800 | — | -.025em | #F5F5F7 |
| 섹션 h2 (일반) | 20px | 800 | — | -.02em | #fff |
| 아티클 본문 h2 | 24px | 800 | 1.3 | -.025em | #fff (좌측 레드 바 포함) |
| 소제목 h3 | 16~18px | 800 | — | -.02em | #fff |
| 카드 타이틀 (기본) | 14.5~16px | 700 | 1.4 | -.01em | #ECECEF |
| 카드 타이틀 (큐레이션 목록) | 19px | 700 | 1.4 | -.015em | #ECECEF |
| 아티클 본문 p | 17px | 400 | 1.85 | -.003em | #c8c8d0 |
| 큐레이션/글 본문 p | 16~16.5px | 400 | 1.85 | — | #cacad2 |
| 아티클 인용문 (blockquote) | 22px | 700 | 1.5 | -.02em | #F5F5F7 (`"..."` 감쌈) |
| 아티클 "한 줄 정의" | 19px | 700 | 1.55 | -.02em | #fff |
| 아티클 리스트 li | 16.5px | 400 | 1.7 | — | #c8c8d0 |
| 히어로 부제 p | 16.5px | 400 | 1.6 | — | rgba(255,255,255,.88) |
| 아티클 히어로 부제 | 17px | 400 | 1.55 | — | rgba(255,255,255,.82) |
| 설명문 (목록 상단) | 15px | 400 | — | — | #9a9aa4 |
| 메타 (카드 하단) | 12.5px | 400 | — | — | #7a7a84 |
| 카테고리 라벨 (mono) | 10.5~12px | 600 | — | .04em | #E8123C |
| 뱃지 (BEST/NEW/level) | 10~11px | 700 | — | — | #fff / #E8123C |
| 가격 (큰) | 18~30px | 800 | — | — | #fff |
| 네비 링크 | 14.5px | 600 | — | — | 활성 #E8123C / 비활성 #a6a6b0 |
| 버튼 (CTA) | 14~16px | 700~800 | — | — | 상황별 |
| 통계 숫자 (대시보드) | 28px | 800 | — | — | #fff |
| 히어로 통계 숫자 | 21px | 800 | — | — | #fff |

### 1.3 간격 · 라운드 (Spacing / Radius)

**컨테이너 최대폭**: 목록/홈 `1180px`, 상세(클래스/큐레이션목록/밋플목록) `1080px`, 결제 `920px`, 밋플상세 `980px`, 커뮤니티목록 `820px`, 아티클 본문 `720px` (props로 620~840 조정), 커뮤니티/큐레이션 상세 `720~740px`, 온보딩 `520px`, 결제완료 `480px`. 모두 `margin:0 auto` 중앙 정렬.

**섹션 패딩**: 데스크톱 좌우 `40px` (`.pad` 클래스, 모바일에서 `18px`로 축소). 헤더는 `14px 28px`. 세로 패딩은 섹션별 `40px 40px 8px` (홈 섹션 간), 히어로 `64px 40px 70px`.

**그리드 gap**: 카드 그리드 `14~18px`. 4열 그리드 `16px`, 3열 `16~18px`, 2열 `14~16px`.

**Radius 패턴**:
| 값 | 용도 |
|---|---|
| 5~6px | 작은 뱃지 (카테고리/level 오버레이) |
| 9~12px | 버튼, 입력창, 밋플 아이콘칩, 검색창 |
| 14px | 카드 (커뮤니티/대시보드/밋플정보), 서피스 박스 |
| 16px | 기본 카드 (큐레이션/클래스/밋플), callout |
| 18px | 구매 박스, 밋플 커버, 키비주얼, 저자카드, "정의" 박스 |
| 20~24px | 칩/pill (알약형), CTA 라운드 버튼 |
| 30px | 히어로 CTA 버튼, 플로팅 스위처 |
| 50% | 아바타 원, 로고 점, 결제완료 체크 원 |

**전역 리셋**: `* { box-sizing:border-box }`, `html,body { margin:0; padding:0 }`.

### 1.4 트랜지션 · 인터랙션 유틸 클래스

```css
.lk   { cursor:pointer; transition:color .15s ease; }
.lk:hover { color:#fff; }
.card { cursor:pointer; transition:transform .18s ease, border-color .18s ease, background .18s ease; }
.card:hover { transform:translateY(-4px); border-color:rgba(232,18,60,.5); }   /* 카드 4px 상승 + 레드 테두리 */
.btn  { cursor:pointer; border:none; font-family:inherit; transition:filter .15s ease, transform .12s ease; }
.btn:hover { filter:brightness(1.08); }
.btn:active { transform:scale(.97); }
.ghost:hover { background:rgba(255,255,255,.06); }   /* 외곽선 버튼 */
.chip { cursor:pointer; transition:all .15s ease; }
.pill:hover { background:rgba(255,255,255,.08); }
/* 아티클 상세 전용 */
.actn:hover   { background:rgba(255,255,255,.09) !important; color:#fff !important; }
.tagchip:hover{ background:rgba(232,18,60,.14) !important; color:#F4788F !important; border-color:rgba(232,18,60,.4) !important; }
```

스크롤바: `width/height:10px`, 썸 `#26262e` radius 6px, 트랙 `#0e0e12`.

### 1.5 그라디언트 팔레트 (카드 썸네일 시스템)

실제 이미지가 없는 카드(아티클/클래스/밋플/아바타)는 인덱스 기반 그라디언트로 썸네일을 만든다. `grads(i)` = 8색 순환 (`i % 8`):

```
0: linear-gradient(135deg,#E8123C,#7A0A22)   // 레드
1: linear-gradient(135deg,#3E3FD9,#1A1A6E)   // 블루
2: linear-gradient(135deg,#1F8A5B,#0C3D28)   // 그린
3: linear-gradient(135deg,#D98324,#5A360C)   // 오렌지
4: linear-gradient(135deg,#8B2FC9,#3A0F58)   // 퍼플
5: linear-gradient(135deg,#1593A6,#093E47)   // 틸
6: linear-gradient(135deg,#C2185B,#5A0A2A)   // 마젠타
7: linear-gradient(135deg,#455A64,#1C2429)   // 그레이
```

오프셋: 클래스는 `grads(i)`, 아티클은 `grads(i+2)`, 커뮤니티 아바타는 `grads(i+1)`, 밋플은 `grads(i+3)`. 밋플/핫딜은 실제 이미지가 있으면 `center/cover no-repeat url(img), <grad>` 형태로 그라디언트 위에 이미지를 얹는다 (이미지 로드 실패 시 그라디언트 폴백).

---

## 2. 홈 SPA 구조 (라우트 상태 머신)

단일 상태 `route` 값으로 뷰를 전환하는 클라이언트 SPA. 초기 상태:

```js
state = { route:'home', classId:null, articleId:null, postId:null, eventId:null,
  cat:'전체', user:null, enrolled:[], comments:{}, paid:false, hdCat:'전체',
  obStep:1, obRole:'직장인', obInterests:[], payClassId:null, payDone:false }
```

**네비게이션**: `go(route, extra)` → `setState({route, ...extra})` + `window.scrollTo(0,0)`.

**라우트 값 목록**: `home`, `classes`, `class-detail`, `curation`, `curation-detail`, `community`, `community-detail`, `meet`, `meet-detail`, `hotdeal`, `onboarding`, `checkout`, `dashboard`.

**숫자 포맷**: `fmt(n)` = `n.toLocaleString('ko-KR')` (천단위 콤마).

### 2.1 전역 상단 네비 (모든 뷰 공통)

스티키 헤더 (`position:sticky; top:0; z-index:50`), `padding:14px 28px`, 배경 `rgba(8,8,11,.82)` + blur(14px), 하단 테두리.

구성 (좌→우):
1. **로고**: 레드 점(11px 원 `#E8123C`) + "NEXUS" (21px/800/#fff) — 클릭 시 홈.
2. **네비 링크** (`.topnav-links`, 22px gap, 14.5px/600): 홈 · 큐레이션 · 클래스 · 커뮤니티 · meet.pl · AI핫딜 · `eat.pl ↗`(외부링크 `https://web.paybooc.ai/place/what-to-eat`). 활성 라우트는 `#E8123C`, 나머지 `#a6a6b0`. (eat.pl은 항상 `#a6a6b0`)
   - 활성 판정: 큐레이션은 `curation`+`curation-detail`, 클래스는 `classes`+`class-detail`, 커뮤니티는 `community`+`community-detail`, 밋플은 `meet`+`meet-detail`.
3. **flex spacer** (`flex:1`).
4. **검색창** (`.hidemob`, 210px, `#141419` 배경): `⌕ 무엇을 배워볼까요?` (클릭 시 클래스로 이동).
5. **로그인 링크** (`.topnav-cta`): 텍스트 = `user||'로그인'`, 색 = 로그인 시 `#fff` 아니면 `#d2d2da` → 온보딩으로.
6. **CTA 버튼** (`.topnav-cta`, 흰 배경/레드 텍스트, radius 24px): 텍스트 = `user?'내 학습':'시작하기'` → 온보딩(로그인 시 대시보드).
7. **햄버거 버튼** (`.burger`, 기본 숨김, 모바일만 표시, 40x40 `#141419`): 클릭 시 클래스 목록.

로그인 로직: `goOnboarding` = 이미 user 있으면 대시보드, 없으면 온보딩.

### 2.2 전역 모바일 하단 네비 (`.mobnav`)

`position:fixed; bottom:0; z-index:60`, 기본 `display:none` → 모바일에서만 표시. 5개 아이콘 항목 (세로 아이콘+라벨, 10.5px): ⌂ 홈 · ▦ 클래스 · ✎ 커뮤니티 · ◎ meet.pl · ☰ MY(대시보드). 활성 색 `#E8123C`.

### 2.3 홈 뷰 (`route === 'home'`)

#### (a) 히어로 섹션
`padding:64px 40px 70px`, 배경 = `radial-gradient(130% 150% at 82% -10%, #FF1E4E 0%, #C00E30 32%, #5A0819 60%, #100A0D 92%)` (우상단 밝은 레드→어두운 검붉은색). `overflow:hidden`. 내부 그리드 `max-width:1180px`.
- **좌측 (max 580px)**:
  - 뱃지 (mono, `rgba(255,255,255,.16)` 배경 알약): `AFTER WORK, LEVEL UP`
  - h1 (52px): "퇴근 후 30분,<br>금융 AI 한 스푼."
  - 설명 p (16.5px, rgba white .88): "BC카드 실거래 데이터로 배우고, 현직자와 토론하고, 사내 프로젝트로 연결돼요. 직장인과 개발자를 위한 가장 실무적인 금융 AI 학습 채널."
  - 버튼 2개: "무료로 시작하기"(흰배경/레드텍스트, radius 30px → 온보딩) + "클래스 둘러보기"(ghost, 1.5px 반투명 흰 테두리 → 클래스)
  - **통계 3개** (26px gap): `38만 건` / 실습용 익명 거래 데이터 · `120+` / 금융·AI 실무 클래스 · `9,400+` / 수강생·현직자 커뮤니티
- **우측 플로팅 카드** (`.herocards`, absolute right, 300px, 모바일 숨김): 2개 글래스 카드 (`rgba(12,12,15,.5)` + blur):
  1. `LIVE 커뮤니티` / "사내에서 RAG 도입한 후기 (삽질 포함)" / "지금 23명 보는 중" → 커뮤니티
  2. `인기 클래스` / "이상거래 탐지(FDS) 모델 만들기" / "수강생 1,580명 · 4.9★" → 클래스

#### (b) 섹션들 (각 `max-width:1180px`, 헤더 = h2 + "더보기 →" 링크)
1. **✦ 나를 위한 큐레이션** (3열 그리드 `.rgrid-3`) — `homeArticles` = 아티클 첫 3개. 카드: 상단 124px 그라디언트 + 카테고리(mono/레드) + 타이틀(15.5px) + `{source} · {readTime}`. → 큐레이션 상세.
2. **🔥 지금 뜨는 클래스** (4열 `.rgrid-4`) — `hotClasses` = 클래스 [c4, c1, c2, c6] 고정 순서. 카드: 120px 그라디언트(좌상단 카테고리 뱃지) + 타이틀 + `{instructor} · {rating}★` + 하단 tag(레드) + 가격(우측). 가격 표기: 100만원 이상은 "만원" 단위(예 390만원), 미만은 "원". → 클래스 상세.
3. **💬 이번 주 커뮤니티** (2열 `.rgrid-2`) — `homePosts` = 글 첫 4개. 카드: 좌측 50px 원형 아바타(그라디언트+이니셜) + 타이틀 + `{tag} · 좋아요 {likes} · 댓글 {commentCount}`. → 커뮤니티 상세.
4. **📍 가야할 밋플** (3열) — `homeEvents` = 이벤트 첫 3개. 카드: 120px 이미지/그라디언트(하단 날짜뱃지) + 타이틀 + `{location} · {going}명 참여`. → 밋플 상세.

#### (c) 푸터 밴드
`#0C0C10` 배경, 중앙 정렬: "금융과 AI, 일하면서 배웁니다." (18px/800) + "BC카드 AI 사업팀 · NEXUS — credit + finance" (13px/#6a6a74) + 링크 6개(클래스·큐레이션·커뮤니티·meet.pl·AI핫딜·eat.pl).

### 2.4 클래스 목록 (`classes`)

`max-width:1180px`. 상단: mono 라벨 `CLASS · 데이터사이언스 / AI` + h1 "금융 AI 클래스" + 설명. **카테고리 칩** (`classCats`): `전체, 데이터 분석, LLM·생성형 AI, 금융 도메인, 생산성, 커리어, 부트캠프`. 활성 칩 = 배경 `#E8123C`/텍스트 흰색/테두리 레드, 비활성 = 배경 `#15151A`/텍스트 `#b4b4be`/테두리 `rgba(255,255,255,.08)`. 클릭 시 `setState({cat})`.
카운트 텍스트: `{cat} · 총 {n}개 클래스`.
**클래스 그리드** (3열): 카드 = 148px 그라디언트(좌상단 카테고리 뱃지 + 우상단 level 뱃지) + tag(레드, 13px 높이 고정) + 타이틀(16px) + `{instructor} · {chapters}개 챕터 · {rating}★` + 가격(18px/800). 필터: `cat==='전체'`면 전체, 아니면 `category===cat`.

### 2.5 클래스 상세 (`class-detail`, classId 필요)

- 상단 배너 `#0E0E13` + "← 클래스 목록" 링크 (max 1080px).
- **2단 그리드** (`.detailgrid`, `1.5fr .9fr`, gap 34px):
  - **좌측**: mono `{category} · {level}` + h1(30px) + desc(15.5px/`#b4b4be`) + 메타행(👩‍🏫 강사 · 📚 {chapters}개 챕터 · {hours}시간 · ⭐{rating} · 👥{students}명 수강) + 240px 그라디언트 박스("[ 강의 인트로 영상 ]") + h2 "커리큘럼" + 커리큘럼 리스트(테두리 박스 안 행들: `01` 넘버(레드/mono) + 챕터명(15px/600) + ▶ 아이콘). 커리큘럼은 category별로 다름 (2.11 참조).
  - **우측 스티키 구매박스** (`position:sticky; top:90px`, `#15151A`): 원가(취소선, `original>0`일 때만) + 가격(30px/800) + "수강 신청하기" 버튼(레드, full) + "구독으로 전체 수강" 버튼(ghost) + 혜택 리스트 4개: ✓ 평생 소장·무제한 반복 수강 / ✓ BC카드 실데이터 실습 환경 제공 / ✓ 수료증 발급·커뮤니티 멤버십 / ✓ 비씨카드 결제 시 5% 청구할인.
- **수강 신청**: `enroll(c)` → enrolled 배열에 `{id, progress:0~24 랜덤}` 추가 → 체크아웃으로 이동(`payClassId`).

### 2.6 큐레이션 목록 (`curation`)

`max-width:1080px`. mono `CURATION · 테크 & 비즈니스 인사이트` + h1 "나를 위한 큐레이션" + 설명 "매일 업데이트되는 AI 테크 강좌와 금융·커리어 인사이트. 출근길에 한 편씩." **가로형 리스트 카드** (`allArticles` 전체, 세로 스택, `margin-bottom:14px`): 좌측 200px 그라디언트(모바일 숨김) + 우측 패딩 영역(카테고리 mono + 타이틀 19px + excerpt 14px/`#9a9aa4` + `{source} · {readTime} 읽기`). → 큐레이션 상세.

### 2.7 큐레이션 상세 (`curation-detail`, articleId 필요)

`max-width:740px`. "← 큐레이션" + 카테고리(mono/레드) + h1(34px) + 저자행(34px 원형 그라디언트 + `{source} · {readTime} 읽기`, 하단 구분선) + 280px 그라디언트 히어로 박스 + 본문(16.5px/1.85, para 배열을 gap 22px로 나열) + "함께 읽으면 좋은 글" (3열, 자기 제외 3개: 80px 그라디언트 + 타이틀). 본문은 `articleBody()` 고정 4문단 (2.11 참조).
> 참고: 이 뷰는 홈 앱 내부의 간단한 아티클 뷰. 진짜 리치한 아티클은 별도 **아티클 상세 앱**(섹션 4).

### 2.8 커뮤니티 목록 (`community`)

`max-width:820px`. 상단행: mono `COMMUNITY · 직접 쓰는 노하우` + h1 "커뮤니티" / 우측 "✎ 글쓰기" 버튼(레드, 클릭 시 alert 프로토타입). 설명 "팁·기술자료·삽질 후기까지. 현직자들이 직접 등록하고 댓글로 나눕니다." **글 카드** (세로 스택, gap 14px): 좌측 46px 원형 아바타 + 태그칩(mono, `rgba(232,18,60,.12)` 배경) + `{author} · {time}` + 타이틀(17px) + `♥ {likes} · 💬 {commentCount}`. → 커뮤니티 상세.

### 2.9 커뮤니티 상세 (`community-detail`, postId 필요)

`max-width:720px`. "← 커뮤니티" + 저자행(46px 아바타 + 이름 + `{tag} · {time}`) + h1(26px) + 본문(16px/1.85, `white-space:pre-line`) + 액션 pill 3개(♥ 좋아요 {likes} / 🔖 저장 / ↗ 공유) + "댓글 {n}" + **댓글 입력**(input `#15151A` + "등록" 버튼 레드) + 댓글 리스트(36px 회색 원형 아바타(`#26262e`) + 이니셜 + 이름 + 내용).
**댓글 추가**: `addComment(postId)` → input 값 trim, 비어있으면 무시, `comments[postId]`에 `{a:user||'나', t:value}` push, input 클리어.

### 2.10 밋플 목록 (`meet`) & 상세 (`meet-detail`)

**목록** (`max-width:1080px`, 3열): mono `meet.pl · AI 이벤트 & 밋업` + h1 "가야할 밋플" + 설명. 카드: 140px 이미지/그라디언트(좌상단 tag 뱃지 + 우상단 날짜뱃지) + 타이틀(16px) + host + `📍{location}` + `👥{going}명 참여 예정`.
- 날짜뱃지 = `date`에서 "2026." 제거 + 요일 괄호 제거 (예: `07.15`).

**상세** (`meet-detail`, eventId 필요, `max-width:980px`, 2단 `.85fr 1.15fr`):
- **좌측**: 1:1 정사각 커버(이미지 또는 그라디언트, 이미지 없으면 중앙에 타이틀 텍스트) + 호스트 박스(`#15151A`: "호스트" 라벨 + host).
- **우측**: "← meet.pl" + h1(30px) + **날짜 박스**(`#13131A`, 46px 아이콘칩 mono "DATE" 레드 + `{date}` + `{time}`) + **장소 박스**(📍 아이콘 + `{location}` + `{going}명 참여 예정`) + "참가 신청하기" 버튼(레드, full, 클릭 시 alert) + "이벤트 소개"(desc 15.5px/1.8) + "진행 순서" **타임라인**(좌측 레드 세로선 `rgba(232,18,60,.4)`, 각 행 = mono 시간(레드, min-width 96px) + 내용).

### 2.11 AI핫딜 (`hotdeal`)

배경 `#0A0A12` (푸른 검정). **액센트가 레드가 아닌 블루-보라(`#3E3FD9`/`#6E6FF5`)**. mono `AI HOTPICK · gemma 27B 추천` + h1 "AI 추천 핫딜" + 설명 "매일 업데이트되는 AI 추천 특가 모음 · 총 {n}개 — 수많은 상품 중 지금 가장 혜택 좋은 딜만 골라드립니다." **카테고리 칩**(`hdCats`: 전체, 여행, 식품/건강, 생활/주방, 뷰티/헬스, 패션/잡화, 가전/디지털) — 활성 칩 배경 `#3E3FD9`. **상품 그리드**(4열): 카드 `#12121C`, `aspect-ratio:1.45/1` 이미지(실패 시 숨김, 좌상단 할인율 뱃지 레드 `discount>0`일 때) + `{category} · {channel}`(mono/블루) + 상품명(13.5px, min-height 38px) + 원가(취소선, `original>0`) + 가격(17px/800). 클릭 시 `window.open('https://open.paybooc.co.kr')`. 하단 데이터 출처 각주: "데이터: open.paybooc.co.kr/bcai · BC카드 AI 핫픽 API".

### 2.12 온보딩 (`onboarding`, 3스텝)

`max-width:520px`. 중앙 로고 + **진행바 3칸**(4px 높이, step1 항상 레드, `obBar2`/`obBar3`은 현재 step≥2/3일 때 레드 아니면 `#26262e`).
- **Step 1** (`obStep1`): h1 "반가워요 👋" + "3분이면 충분해요..." + 이름 입력(`nameRef`, placeholder "예) 김크레딧") + "저는..." 역할 선택 2카드(💼 직장인 / ⌨️ 개발자, 선택 시 테두리 레드 `obRole`) + "다음" 버튼.
- **Step 2** (`obStep2`): h1 "관심 분야를 골라주세요" + 관심사 칩(다중선택): `데이터 분석, LLM·생성형 AI, 금융 도메인, 생산성, 커리어, MLOps` — 선택 시 배경/테두리 레드, 텍스트 흰색. "이전"(ghost) + "다음"(레드).
- **Step 3** (`obStep3`): h1 "준비 완료! 🎉" + 멤버십 카드(`#15151A`: 원가 취소선 "29,000원" + "19,900원 / 월" + 혜택 3개: ✓120+ 클래스 무제한 / ✓현직자 커뮤니티&밋플 우선 신청 / ✓비씨카드 결제 시 첫 달 50% 할인) + "무료로 시작하기"(레드) + "나중에 할게요"(텍스트버튼).
- **완료**: `finishOnboarding()` → name 저장(기본 "김크레딧"), obStep 리셋, 대시보드로. `obNext`/`obPrev`로 step 이동(1~3 clamp).

### 2.13 결제 (`checkout`, payClassId 필요)

두 상태: `payDone` false(결제 화면) / true(완료 화면).
- **결제 화면** (`max-width:920px`, 2단 `1.2fr .8fr`):
  - 좌측: "← 클래스" + h1 "결제하기" + "결제 수단" 소제목 + **BC카드 카드 UI**(`linear-gradient(120deg,#E8123C,#8A0A22)`: "BC카드" + "PRIMARY" + mono 카드번호 "5409 •••• •••• 2026" + "KIM CREDIT" + "구독 5% 청구할인 적용") + "+ 다른 카드로 결제"(점선 pill) + "할부 개월" 칩(일시불(활성 레드)/3/6/12개월).
  - 우측 스티키 요약(`#15151A`): 60px 그라디언트 썸네일 + 강의명 + 강의 금액 + "비씨카드 할인 -5%"(그린 `#1F8A5B`) + 최종 결제금액(24px/800) + "{금액} 결제하기" 버튼(레드) + 약관 각주.
  - `doPay()` = `payNow()`: payDone=true, paid=true, user 기본 "김크레딧".
- **완료 화면** (`max-width:480px`, 중앙): 74px 그린 원(`#1F8A5B`) ✓ + h1 "수강 신청 완료!" + "비씨카드로 결제가 완료되었어요..." + "내 학습 대시보드로"(레드) + "다른 클래스 보기"(ghost).

### 2.14 대시보드 (`dashboard`)

`max-width:1080px`. 프로필 헤더(60px 레드 그라디언트 원 + 이니셜 + "{userName}님의 학습" 22px + "이번 주도 한 스푼씩, 꾸준히 가봐요 🍯"). **통계 4개**(`.rgrid-4`, 각 `#15151A`, 28px 숫자): 수강 중인 클래스({myCount}) / 연속 학습 7일🔥 / 작성한 커뮤니티 글 12 / 신청한 밋플 2.
- "이어서 학습하기": 수강 클래스 있으면(`hasClasses`) 진행 카드 리스트(90x60 그라디언트 썸네일 + 타이틀 + **진행바**(7px, 트랙 `#26262e`, 채움 레드, `{progress}%`) + "이어보기" 버튼). 없으면 빈 상태(점선 박스: 📚 + "아직 수강 중인 클래스가 없어요" + "클래스 둘러보기").
- "추천 큐레이션"(3열): `homeArticles` (90px 그라디언트 + 타이틀 + readTime).
- `myClasses` = enrolled를 클래스 데이터와 조인, progress 포함.

---

## 3. 샘플 데이터 (DB 시드용 — 전 필드 전사)

### 3.1 클래스 `classes()` (9개)
필드: `id, title, instructor, category, level, price, original, chapters, hours, rating, students, tag, desc`.

| id | title | instructor | category | level | price | original | chapters | hours | rating | students | tag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| c1 | [오프라인] 직장인 AI 개발자 12주 과정 | NEXUS LAB | 부트캠프 | 올인원 | 3900000 | 0 | 14 | 14 | 4.9 | 88 | BEST |
| c2 | [오프라인] LLM으로 금융 상담 챗봇 만들기 | 이엔지니어 | LLM·생성형 AI | 중급 | 264000 | 390000 | 10 | 18 | 4.8 | 870 | NEW |
| c3 | [오프라인] 카드 매출 데이터로 배우는 시계열 예측 | 박애널 | 데이터 분석 | 중급 | 231000 | 330000 | 6 | 11 | 4.8 | 540 | (없음) |
| c4 | [오프라인] 이상거래 탐지(FDS) 모델 만들기 | 정ML | 금융 도메인 | 중급 | 297000 | 420000 | 9 | 16 | 4.9 | 1580 | BEST |
| c5 | [오프라인] RAG로 사내 규정 검색 시스템 구축 | 최RAG | LLM·생성형 AI | 중급 | 275000 | 0 | 7 | 13 | 4.7 | 430 | NEW |
| c6 | [오프라인] 프롬프트 엔지니어링 실무 워크숍 | 한프롬 | 생산성 | 입문 | 132000 | 190000 | 5 | 8 | 4.6 | 2100 | (없음) |
| c7 | [오프라인] 개인화 추천 시스템: BC카드 API 활용 | 오레코 | 금융 도메인 | 고급 | 330000 | 0 | 11 | 20 | 4.9 | 320 | NEW |
| c8 | [오프라인] 비전공자를 위한 금융 데이터 리터러시 | 윤기초 | 커리어 | 입문 | 99000 | 150000 | 6 | 9 | 4.7 | 3200 | (없음) |
| c9 | [오프라인] 결제 데이터 분석 입문: SQL부터 대시보드까지 | 김데이터 | 데이터 분석 | 입문 | 198000 | 290000 | 8 | 14 | 4.9 | 1240 | (없음) |

**desc 전문**:
- c1: "비전공 직장인을 위한 12주 오프라인 부트캠프. 파이썬 기초부터 머신러닝·LLM 활용까지, 퇴근 후 주말 집중 과정으로 현업 AI 개발자로의 전환을 돕습니다. BC카드 현직 멘토링과 팀 프로젝트, 수료 후 사내 연계 채용 추천까지 포함합니다."
- c2: "gemma 27B와 RAG를 활용해 실제 금융 상담 시나리오를 처리하는 챗봇을 처음부터 끝까지 구축합니다."
- c3: "가맹점 매출 시계열을 다루며 수요 예측 모델을 설계하고, 실제 비즈니스 의사결정에 연결하는 법을 배웁니다."
- c4: "카드 거래의 이상 패턴을 잡아내는 FDS 모델을, 불균형 데이터 처리부터 실시간 추론까지 실무 그대로 구현합니다."
- c5: "사내 문서를 임베딩하고 벡터 DB로 검색하는 RAG 파이프라인을 구축해, 규정/매뉴얼 Q&A 시스템을 완성합니다."
- c6: "업무 자동화에 바로 쓰는 프롬프트 패턴을 익히고, 반복 업무를 LLM으로 처리하는 나만의 템플릿을 만듭니다."
- c7: "BC카드 오픈 API와 소비 데이터를 결합해, 사용자별 혜택·가맹점을 추천하는 개인화 엔진을 설계합니다."
- c8: "숫자가 두려운 직장인을 위한 입문 과정. 금융 데이터를 읽고 해석하는 감각을 비전공자 눈높이에서 기릅니다."
- c9: "12주간 주말 집중. BC카드 데이터로 진행하는 팀 프로젝트와 현직 멘토링, 수료 후 사내 연계 채용 추천까지 포함합니다."

### 3.2 커리큘럼 `curriculum(c)` (category별 고정)
- **LLM·생성형 AI**: 오리엔테이션 & 환경 설정 / LLM 기초와 토크나이저 / 프롬프트 설계 패턴 / RAG 파이프라인 이해 / 벡터 DB & 임베딩 / 금융 도메인 파인튜닝 / 평가와 가드레일 / 배포와 모니터링 (8개)
- **금융 도메인**: 금융 데이터의 특성 / 피처 엔지니어링 / 불균형 데이터 다루기 / 모델 학습과 튜닝 / 실시간 추론 설계 / 성능 평가 & 운영 (6개)
- **그 외(기본)**: 데이터 불러오기 & 정제 / 탐색적 데이터 분석(EDA) / SQL로 집계하기 / 핵심 지표 설계 / 시각화 대시보드 / 인사이트 도출 & 발표 (6개)

### 3.3 큐레이션 아티클 `articles()` (6개, 홈 앱용)
필드: `id, category, title, source, readTime, excerpt`.

| id | category | title | source | readTime |
|---|---|---|---|---|
| a1 | AI 트렌드 | GPT-5 시대, 금융권은 LLM을 어떻게 도입하고 있나 | NEXUS 에디터 | 7분 |
| a2 | 커리어 | 비전공 직장인이 6개월 만에 데이터 분석가로 이직한 법 | 커리어 인사이트 | 5분 |
| a3 | 테크 | RAG vs 파인튜닝, 우리 회사엔 뭐가 맞을까 | NEXUS 에디터 | 8분 |
| a4 | 데이터 리포트 | 결제 데이터로 보는 2026 상반기 소비 트렌드 | 데이터 리포트 | 6분 |
| a5 | 비즈니스 | AI 에이전트가 바꾸는 백오피스 업무 | 비즈니스 인사이트 | 5분 |
| a6 | 테크 | 주니어 개발자가 알아야 할 MLOps 기본기 | NEXUS 에디터 | 9분 |

**excerpt 전문**:
- a1: "규제 산업인 금융에서 생성형 AI를 실서비스에 올리기까지, 국내 주요 금융사들의 도입 전략과 거버넌스를 정리했습니다."
- a2: "엑셀만 쓰던 마케터가 SQL과 파이썬을 익히고 데이터 직무로 전환하기까지의 현실적인 학습 로드맵."
- a3: "비용·정확도·유지보수 관점에서 두 접근을 비교하고, 사내 도입 시 의사결정 체크리스트를 제시합니다."
- a4: "BC카드 익명 통계로 본 세대별 소비 변화. 여행·구독·식품 카테고리에서 두드러진 시그널을 짚어봅니다."
- a5: "정산·리포팅·고객 응대까지, 에이전트가 실제로 대체하기 시작한 업무와 사람이 남겨야 할 일."
- a6: "모델을 만드는 것과 운영하는 것은 다른 문제입니다. 실험 관리부터 배포 파이프라인까지 최소 지식 정리."

**본문 `articleBody()`** (홈 앱 큐레이션 상세 공통 4문단):
1. "많은 조직이 생성형 AI 도입을 검토하지만, 정작 가장 큰 장벽은 모델 성능이 아니라 데이터 거버넌스와 신뢰성입니다."
2. "특히 금융처럼 규제가 강한 산업에서는 "왜 이 답이 나왔는가"를 설명할 수 있어야 하고, 민감 정보가 새지 않도록 가드레일을 촘촘히 세워야 합니다."
3. "실무에서는 작은 범위의 내부 업무(문서 검색, 요약, 초안 작성)부터 시작해 점진적으로 확장하는 전략이 가장 안전합니다."
4. "NEXUS 클래스에서는 이 과정을 BC카드의 실제 익명 데이터로 직접 실습하며, 도입 의사결정에 필요한 감각을 기릅니다."

### 3.4 커뮤니티 글 `posts()` (5개)
필드: `id, title, author, tag, likes, time, body`.

| id | title | author | tag | likes | time |
|---|---|---|---|---|---|
| p1 | 사내에서 RAG 도입한 후기 (삽질 포함) | 데브워커 | 노하우 | 218 | 2일 전 |
| p2 | gemma 27B 로컬 구동 스펙 정리해봤어요 | GPU장인 | 기술자료 | 312 | 4일 전 |
| p3 | 비전공자도 파인튜닝 해봤습니다 | 입문러 | 노하우 | 156 | 5일 전 |
| p4 | 엑셀 대신 파이썬으로 월말 정산 자동화한 썰 | 직장인K | 팁 | 421 | 1주 전 |
| p5 | 프롬프트 템플릿 모음 공유합니다 | 프롬프트수집가 | 자료 | 689 | 1주 전 |

**body 전문**:
- p1: "규정 문서가 수천 페이지라 검색이 지옥이었는데, RAG 붙이고 나서 문의량이 절반으로 줄었습니다. 다만 청킹 전략을 잘못 잡아서 처음엔 엉뚱한 답이 많이 나왔어요. 결국 문서 구조 기반으로 청크를 나누니 정확도가 확 올랐습니다."
- p2: "질문이 많아서 정리합니다. 양자화(4bit) 기준 VRAM 20GB 정도면 무난하게 돌아갑니다. 3090/4090 한 장으로 충분하고, 추론 속도는 토큰당 대략..."
- p3: "문과 출신 기획자입니다. NEXUS LLM 클래스 듣고 처음으로 LoRA 파인튜닝까지 해봤는데, 생각보다 진입장벽이 낮았어요. 데이터셋 만드는 게 제일 오래 걸렸습니다."
- p4: "매달 3일씩 걸리던 정산을 pandas로 자동화했더니 10분이면 끝납니다. 처음엔 무서웠는데 클래스에서 배운 대로 차근차근 하니 됐어요. 코드 공유합니다."
- p5: "업무별로 자주 쓰는 프롬프트를 정리했습니다. 회의록 요약, 이메일 초안, 데이터 해석 요청 등 바로 복붙해서 쓰세요."

**기본 댓글 `defaultComments(id)`** (필드 `a`=작성자, `t`=내용):
- p1: [러너A: "청킹 전략 좀 더 자세히 알 수 있을까요?"], [데브워커: "문서 H2 헤딩 단위로 잘랐어요. 곧 글로 정리할게요!"], [호기심: "문의량 절반 ㄷㄷ 사내 설득 자료로 써도 될까요"]
- p2: [초보: "4bit면 품질 손해 많이 보나요?"], [GPU장인: "체감상 거의 없습니다. 일반 업무용은 충분해요."]
- p4: [정산러: "코드 감사합니다 ㅠㅠ 바로 적용했어요"], [직장인K: "도움 됐다니 다행입니다!"]
- 그 외 기본: [NEXUS: "좋은 글 감사합니다 👏"]

### 3.5 밋플 이벤트 `events()` (5개)
필드: `id, title, host, date, time, location, going, tag, img(선택), desc, schedule[[시간,내용]...]`.

| id | title | host | date | time | location | going | tag |
|---|---|---|---|---|---|---|---|
| e1 | OpenAI Codex 밋업 - 서울 | Dev Korea x NEXUS | 2026.07.15 (화) | 오후 6:30 – 9:15 | MARU180, 강남 | 142 | AI |
| e2 | NEXUS 금융 AI 나이트 | NEXUS | 2026.07.22 (화) | 오후 7:30 – 9:30 | BC카드 본사, 을지로 | 88 | 금융 AI |
| e3 | 판교 LLM 스터디 #12 | 판교AI | 2026.07.10 (목) | 오후 8:00 – 10:00 | 판교 스타트업캠퍼스 | 56 | 스터디 |
| e4 | 데이터 분석가 커리어 토크 | 데이터리안 | 2026.07.18 (금) | 오후 7:00 – 8:30 | 온라인 (Zoom) | 230 | 커리어 |
| e5 | 바이브코딩 해커톤 2026 | NEXUS x Dev Korea | 2026.08.02 (토) | 오전 10:00 – 오후 8:00 | 코엑스, 삼성동 | 320 | 해커톤 |

**img** (e1, e2만 있음):
- e1: `https://images.lumacdn.com/cdn-cgi/image/format=auto,fit=cover,dpr=1,background=white,quality=75,width=400,height=400/uploads/s3/ddff55c2-c5ba-4d48-8810-54c394bb60f1.png`
- e2: `https://images.weserv.nl/?url=news.nateimg.co.kr/orgImg/bt/2026/06/29/666808_279461_3154.jpg`
- e3, e4, e5: 이미지 없음(그라디언트).

**desc 전문**:
- e1: "OpenAI의 소프트웨어 엔지니어링 에이전트 Codex를 주제로 한 저녁 행사. 최신 업데이트와 라이브 데모, 파워 유저를 위한 실용 팁을 공유합니다. 실시간 통역 제공."
- e2: "BC카드 데이터로 만든 프로젝트 쇼케이스와 현직자 라이트닝 토크. 수강생 네트워킹 세션이 이어집니다."
- e3: "매주 진행하는 LLM 논문/실습 스터디. 이번 주제는 효율적 파인튜닝(PEFT)과 LoRA 변형들."
- e4: "현직 데이터 분석가 3인이 들려주는 직무 전환과 포트폴리오 이야기. Q&A 중심으로 진행됩니다."
- e5: "AI 에이전트와 함께 하루 만에 금융 서비스를 만드는 해커톤. BC카드 API 제공, 우승팀 사내 연계 기회."

**schedule** (진행 순서):
- e1: [6:30–7:00 체크인 & 식사], [7:00–7:05 행사 소개], [7:05–7:40 Valuemaxxing with Codex], [7:40–8:10 세션 #2], [8:10–8:25 커뮤니티 데모], [8:30–9:15 네트워킹]
- e2: [7:30–8:00 웰컴 & 등록], [8:00–8:40 프로젝트 쇼케이스], [8:40–9:10 라이트닝 토크], [9:10–9:30 네트워킹]
- e3: [8:00–8:10 인트로], [8:10–9:00 논문 리뷰], [9:00–9:50 코드 실습], [9:50–10:00 정리]
- e4: [7:00–7:10 오프닝], [7:10–8:00 패널 토크], [8:00–8:30 라이브 Q&A]
- e5: [10:00 킥오프 & 팀 빌딩], [11:00 해킹 시작], [17:00 제출 마감], [17:30 데모 & 심사], [19:00 시상 & 네트워킹]

### 3.6 핫딜 `deals()` (12개)
필드: `name, price, original, discount(%), category, channel, img`.

| name | price | original | discount | category | channel |
|---|---|---|---|---|---|
| 보라카이 4일 (노쇼핑·호핑투어) | 529900 | 0 | 0 | 여행 | 노랑풍선 |
| 푸꾸옥 인터컨티넨탈 에어텔 5/6일 | 929000 | 1858000 | 50 | 여행 | 노랑풍선 |
| 클럽메드 푸켓 올인클루시브 3박5일 | 1140000 | 0 | 0 | 여행 | 노랑풍선 |
| 다낭/호이안 5/6일 (부산 출발) | 659000 | 0 | 0 | 여행 | 노랑풍선 |
| 스탠리 퀜처 H2.0 텀블러 591ml | 23760 | 43200 | 40 | 생활/주방 | 네이버 |
| 오레오 600g x 2개 | 9140 | 18900 | 52 | 식품/건강 | 쿠팡 |
| 쿤달 이중미세모 칫솔 12개입 2세트 | 20900 | 41000 | 49 | 뷰티/헬스 | G마켓 |
| 페레로로쉐 (5T x 12) x 2 | 35900 | 0 | 14 | 식품/건강 | 떠리몰 |
| 유니클로 박시 크롭 티셔츠 1+1 | 26200 | 0 | 0 | 패션/잡화 | 유니클로 |
| 매일 어메이징오트 190ml 54팩 | 20940 | 0 | 0 | 식품/건강 | 롯데온 |
| 벡셀 알카라인 건전지 AA 48알 | 11740 | 0 | 0 | 생활/주방 | 지마켓 |
| 비브르 탁상용 선풍기 7000mAh | 36160 | 0 | 6 | 가전/디지털 | G마켓 |

img URL (재현 시 필요하면 실 URL 사용, 없으면 플레이스홀더):
- 보라카이: `https://dimgcdn.ybtour.co.kr/TN/ee/ee36359db90b602bac23fe63a8faf511.tn.410x280.JPG`
- 푸꾸옥: `.../85/85037d241c2e91675082bee8efdd6562.tn.410x280.jpeg`
- 클럽메드: `.../71/710432c6e3124b2a5916eff2138178e4.tn.410x280.jpg`
- 다낭: `.../79/798308110f991d072ac7a24eea0e6da9.tn.410x280.jpg`
- 스탠리: `https://cdn89.dasaja.co.kr:4443/files/shop_item_img/1775117163.jpg`
- 오레오: `.../1782760865.jpg`, 페레로: `.../1782755344.jpg`, 유니클로: `.../1782749048.jpg`
- 쿤달: `https://cdn2.ppomppu.co.kr/zboard/data3/2026/0630/m_20260630091345_OD1Jo4Ag5j.png`
- 어메이징오트: `.../m_20260630090732_XOpv0YvQOR.jpg`, 건전지: `.../m_20260630091837_uqd35AapIV.png`
- 비브르 선풍기: `https://cdn89.dasaja.co.kr:4443/files/shop_item_img/1781048888.jpg`

### 3.7 온보딩 옵션
- 역할: `직장인`, `개발자`.
- 관심사(다중): `데이터 분석, LLM·생성형 AI, 금융 도메인, 생산성, 커리어, MLOps`.

---

## 4. 아티클 상세 페이지 (독립 앱 — 리치 에디토리얼)

홈 앱과 별개인 독립 페이지. 3개의 프리미엄 에디토리얼 아티클을 유형 스위처로 전환. state: `{ article:'a1', liked:false, saved:false }`.

**프롭스** (외부 설정 가능): `readingWidth`(기본 720, 범위 620~840), `showProgress`(기본 true), `heroMotion`(기본 true — false면 애니메이션 정지).

### 4.1 레이아웃 골격
1. **상단 네비** (홈과 동일, `z-index:60`, 큐레이션 활성). 검색창 190px.
2. **읽기 진행바** (`showProgress`): `position:sticky; top:57px; z-index:55`, 높이 3px, 트랙 `rgba(255,255,255,.05)`. 내부 `#readprog`가 스크롤 비율만큼 채워짐. 채움색 `linear-gradient(90deg,#E8123C,#FF5A7A)`, `transition:width .1s linear`.
   - JS: `window.scroll` 리스너가 `scrollTop/(scrollHeight-clientHeight)*100`을 계산해 `#readprog` width 갱신 (passive, 마운트 시 1회 즉시 호출).
3. **애니메이션 히어로** (height 460px, 모바일 360/300px).
4. **메타 바** (max 720px): 저자 아바타 + 이름/역할 + 날짜/읽기시간 + mono "조회 {views} · 좋아요 {likeCount}".
5. **액션 행**: 좋아요 / 저장 / (spacer) / 공유 버튼.
6. **키비주얼** (max `readW`px, height 300px): 아티클별 개념 애니메이션.
7. **본문 프로즈** (max `readW`px): 블록 렌더링.
8. **참고한 원 보도 / 면책 / 태그 / 저자 카드**.
9. **함께 읽으면 좋은 글** (max 1180px, 2열).
10. **플로팅 유형 스위처** (`position:fixed; bottom:22px; 중앙`).

### 4.2 애니메이션 히어로 (키비주얼과 별개, 상단 460px 배너)
`background:{theme.heroBase}` 위에 절대배치 레이어:
- **blobA**: 좌상단 620px 원, `filter:blur(50px)`, opacity .75, `animation:drifta 17s ease-in-out infinite`.
- **blobB**: 우상단 520px 원, blur(55px), opacity .7, `driftb 21s`.
- **blobC**: 하단중앙 460px 원, blur(48px), opacity .6, `driftc 15s`.
- **ring**: 우상단 340px 원뿔 그라디언트(`theme.ring`) + radial mask로 링 형태, opacity .55, `spin 26s linear`.
- **grid dots**: `radial-gradient(rgba(255,255,255,.14) 1px, transparent 1px)` 28px 격자, opacity .14, `gridpan 12s linear` (배경 이동).
- **하단 페이드**: `linear-gradient(180deg, transparent 30%, rgba(8,8,11,.55) 72%, #08080B 100%)`.
- 모든 애니메이션은 `animation-play-state:{heroPlay}` (heroMotion=false면 paused).
- **텍스트** (`heroinner`, max 1180px): chip(mono `{koType} · {theme.name}` + section) + h1(46px) + subtitle. chip/title/sub에 `fadeup` 진입 애니메이션 (chip .6s, title .7s, sub .7s+.12s delay).

키프레임:
```css
@keyframes drifta { 0%,100%{transform:translate(0,0) scale(1)} 50%{transform:translate(60px,40px) scale(1.15)} }
@keyframes driftb { 0%,100%{transform:translate(0,0) scale(1.1)} 50%{transform:translate(-70px,30px) scale(.9)} }
@keyframes driftc { 0%,100%{transform:translate(0,0) scale(1)} 50%{transform:translate(30px,-50px) scale(1.2)} }
@keyframes spin { to{transform:rotate(360deg)} }
@keyframes gridpan { from{background-position:0 0} to{background-position:28px 28px} }
@keyframes fadeup { from{opacity:0;transform:translateY(18px)} to{opacity:1;transform:translateY(0)} }
```

### 4.3 키비주얼 (개념 애니메이션, height 300px, 모바일 220/190px)
컨테이너: `#0B0B10` 배경, radius 18px, 테두리 `rgba(255,255,255,.08)`. **순수 CSS + div 기반** (SVG 아님). 아티클별로 다른 다이어그램:

**Figure A (a1 · 리서치 — 역량의 밀도, DENSE/SPARSE/BALANCE)**:
- 좌측: 조밀한 점 격자(`radial-gradient(rgba(124,107,255,.6) 1.5px)` 15px 간격) + 좌→우 fade mask(왼쪽만 보임).
- 우측: 성긴 점 격자(46px 간격, 흰 점) + 우측 fade mask.
- 스캔 라인: 16% 폭 세로 그라디언트가 좌우 이동 (`scanx 5.5s`).
- 중앙 코어: 120px 레드 원(`radial-gradient(rgba(232,18,60,.92))`) blur(5px), `pulseCore 3.2s` (스케일 1→1.24).
- mono 라벨: 좌상 `DENSE`(#B9AEFF), 우상 `SPARSE`(#7a7a86), 하단중앙 `BALANCE`(#F4788F).

**Figure B (a2 · 뉴스레터 — 갈라진 두 스택 → HBM 메모리 길목)**:
- 상단 중앙에 두 세로 레인(폭 4px, 높이 150px, 140px 간격, 모바일 96px):
  - STACK A (좌, `rgba(24,194,156,.22)` 트랙): 그린 점(`#4FE3C1`, `box-shadow:0 0 14px #18C29C`) 3개가 위→아래로 낙하 (`fall 2.2s`, delay 0/.9s/1.5s). 상단 라벨 "STACK A".
  - STACK B (우, `rgba(232,18,60,.22)`): 레드 점(`#F4788F`) 3개 낙하 (delay .4/1.2/1.8s). 라벨 "STACK B".
- 하단 바: `left/right:14%`, 높이 18px, `linear-gradient(90deg,#18C29C,#E8123C)`, `barglow 3s` (glow 펄스). 그 아래 mono 라벨 "MEMORY · HBM" (흰색).

**Figure C (a3 · 칼럼 — 날개)**:
- 배경 오렌지 점 격자(34px, opacity .5).
- 중앙 날개: 좌우 두 개의 날개 모양 div(150x96px, `border-radius:6px 100% 6px 100%` / 반대, `rotate ∓8deg`, 오렌지→레드 그라디언트, glow) + 중앙 26px 코어 원(`radial-gradient(#FFD9A6,#FF9F43)`). 전체 `wingfloat 5s`(상하 유영), 날개 `feather 3.4s`(opacity), 코어 `riseCore 3s`(상승).
- 상단에 작은 입자 2개 (`riseCore` delay).

키비주얼 키프레임:
```css
@keyframes pulseCore { 0%,100%{transform:translate(-50%,-50%) scale(1);opacity:.82} 50%{transform:translate(-50%,-50%) scale(1.24);opacity:1} }
@keyframes scanx { 0%{left:-18%} 100%{left:100%} }
@keyframes fall { 0%{top:-12px;opacity:0} 12%{opacity:1} 88%{opacity:1} 100%{top:100%;opacity:0} }
@keyframes barglow { 0%,100%{opacity:.72;box-shadow:0 0 18px rgba(232,18,60,.35)} 50%{opacity:1;box-shadow:0 0 40px rgba(232,18,60,.65)} }
@keyframes wingfloat { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-9px)} }
@keyframes riseCore { 0%,100%{transform:translateY(0);opacity:.85} 50%{transform:translateY(-12px);opacity:1} }
@keyframes feather { 0%,100%{opacity:.55} 50%{opacity:1} }
```
figcaption (mono, 11.5px, `#6a6a74`): `art.figCaption`.

### 4.4 본문 블록 타입 (`blocks[]`, gap 24px)
각 블록 `{t, x, items, label}`:
| type | 렌더링 |
|---|---|
| `p` | `<p>` 17px/1.85/`#c8c8d0`, letter-spacing -.003em |
| `h2` | 24px/800/#fff, 좌측 레드 바(5x22px, radius3) + 텍스트 (flex) |
| `q` | `<blockquote>` 22px/700/`#F5F5F7`, 좌측 3px 레드선, `"..."` 감쌈 |
| `ul` | `list-style:none`, gap12, 각 li 16.5px + 좌측 7px 레드 사각 불릿 |
| `call` (callout) | `#131318` 박스, radius16, mono 라벨(레드/`b.label`) + 본문 16px/`#d3d3db` |
| `def` (한 줄 정의) | `linear-gradient(135deg, rgba(232,18,60,.14), rgba(232,18,60,.03))` 배경 + 레드 테두리, radius18, mono "한 줄 정의"(`#F4788F`) + 텍스트 19px/700/#fff |

### 4.5 하단 요소
- **참고한 원 보도** (`hasSources`): mono 라벨 "참고한 원 보도" + `—` 불릿 리스트(13.5px/`#9a9aa4`).
- **면책** (`hasDisclaimer`): 12px 이탤릭 `#6a6a74`.
- **태그** (`tagchip`): `#태그` 알약칩, hover 시 레드. 
- **저자 카드** (`authorcard`): `#131318`, 54px 아바타(그라디언트) + 이름(15.5px/800) + bio + "구독" 버튼(레드 알약).
- **함께 읽으면 좋은 글** (2열): 자기 제외한 아티클, 좌측 120px 그라디언트(`theme.relGrad`, 흰점 도트 오버레이) + koType(mono/`relCol`) + 타이틀(16px) + `{author} · {readTime}`. 클릭 시 `setArticle(id)`.
- **플로팅 유형 스위처**: `rgba(18,18,22,.9)` + blur, radius30, shadow. mono "유형" 라벨(모바일 숨김) + 유형 버튼들(활성 배경 레드/흰텍스트, 비활성 투명/`#b6b6c0`). 클릭 시 해당 아티클로 전환.

### 4.6 좋아요 / 저장 / 공유 동작
- **좋아요** (`toggleLike`): liked 토글. 활성 시 배경 `rgba(232,18,60,.16)`, 텍스트 `#F4788F`, 테두리 `rgba(232,18,60,.5)`. 비활성 시 배경 `rgba(255,255,255,.05)`, 텍스트 `#c9c9d2`. **likeCount = rawLikes + (liked?1:0)**, 영문 콤마 포맷(`toLocaleString('en-US')`).
- **저장** (`toggleSave`): saved 토글. 색상 좋아요와 동일. 라벨 = `saved?'저장됨':'저장'`.
- **공유**: 정적 버튼(핸들러 없음, 항상 기본 스타일).
- 아티클 전환 시(`setArticle`) liked/saved 초기화 + smooth 스크롤 top.

### 4.7 아티클 데이터 (3개 전문)
공통 필드: `id, koType, section, title, subtitle, figCaption, author{name,role,initial,avatarBg,bio}, date, readTime, rawViews, rawLikes, tags[], theme{...}, blocks[], sources[], disclaimer`.

**a1 · 리서치 · "앤스로픽의 역설"**
- section "AI · 산업 분석", subtitle "프런티어 벤치마크 1위가, 시장에서 가장 불리한 자리일 수도 있는 이유"
- figCaption "개념도 — 역량의 밀도: 너무 조밀하거나(dense), 너무 흩어지거나(sparse)"
- author: 지적 지니 / AI 리서처 / 이니셜 "지" / avatarBg `linear-gradient(135deg,#7C6BFF,#3A2E8E)` / bio "모델·시장·자본의 교차점을 추적하는 AI 산업 분석 뉴스레터를 씁니다."
- date 2026.07.07, readTime 4분, rawViews 12840, rawLikes 326
- tags: 프런티어 모델, 시장 구조, 에이전트, 멀티모달
- theme: name RESEARCH, chipBg `rgba(124,107,255,.18)`, chipCol `#B9AEFF`, heroBase `radial-gradient(120% 130% at 15% 8%, #2A1E6E 0%, #160E33 40%, #0A0710 74%)`, blobA `radial-gradient(circle, rgba(124,107,255,.95), transparent 68%)`, blobB `radial-gradient(circle, rgba(232,18,60,.85), transparent 66%)`, blobC `radial-gradient(circle, rgba(124,107,255,.6), transparent 70%)`, ring `conic-gradient(from 0deg, #7C6BFF, #E8123C, #7C6BFF)`, relGrad `linear-gradient(135deg,#7C6BFF,#2A1E6E)`, relCol `#B9AEFF`
- blocks: p, h2("첫 번째 벽 — 가격"), p, p, q, h2("두 번째 벽 — 유동적인 시장"), p, h2("세 번째 벽 — 멀티모달 공백"), p, call("한눈에 보기"), def
- sources: ["Artificial Analysis — Intelligence Index", "Axios · Ramp — 기업 AI 지출 데이터", "Stanford CRFM — Foundation Model 보고서"], disclaimer 없음
- 주요 인용문(q): "미래의 승자는 가장 똑똑한 모델이 아니라, 사용자가 가장 오래 켜두는 모델일지 모른다." / 정의(def): "가장 잘하는 분야로 흥한 회사는, 그 분야만 가장 잘하게 될 위험도 함께 짊어진다."

**a2 · 뉴스레터 · "엔비디아 없이 훈련된 AI"**
- section "반도체 · 투자", subtitle "수출통제의 벽에 생긴 균열, 그리고 자금이 다시 고이는 길목"
- figCaption "개념도 — 둘로 갈라진 연산 스택이 모두 지나는 길목, 메모리(HBM)"
- author: 글쓰는 범고래 / 산업 애널리스트 / 이니셜 "범" / avatarBg `linear-gradient(135deg,#18C29C,#0A5647)` / bio "반도체·에너지·자본 흐름을 하나의 지도로 엮는 산업 인사이트를 연재합니다."
- date 2026.07.07, readTime 4분, rawViews 20310, rawLikes 512
- tags: 반도체, 수출통제, HBM, 투자
- theme: name NEWSLETTER, chipBg `rgba(24,194,156,.18)`, chipCol `#4FE3C1`, heroBase `radial-gradient(120% 130% at 15% 8%, #0C5A49 0%, #08352B 42%, #07120F 76%)`, blobA `rgba(24,194,156,.92)`, blobB `rgba(232,18,60,.8)`, blobC `rgba(24,194,156,.55)`, ring `conic-gradient(from 0deg, #18C29C, #E8123C, #18C29C)`, relGrad `linear-gradient(135deg,#18C29C,#0A5647)`, relCol `#4FE3C1`
- blocks: call("3줄 요약"), h2("무슨 일이 있었나"), p, p, h2("이건 "모델"이 아니라 "벽"의 이야기다"), p, q, h2("두 개의 스택, 그리고 남은 격차"), p, h2("그래서 돈은 어디로 흐르는가"), p, ul(3개), def
- ul items: ["연산 칩 — 표준은 여전하지만, 처음으로 "열등하지만 작동하는 대안"이 등장했다", "공통 병목 — 메모리·패키징·파운드리, 어느 시나리오에서도 붐비는 가장 단단한 자리", "소프트웨어 생태계 — CUDA라는 진짜 해자이자, 가장 넘기 어려운 마지막 벽"]
- sources: ["메이투안 LongCat 모델 카드 및 공개 발표 (2026.6)", "모건스탠리 — 중국 AI 칩 성능 비교", "골드만삭스 · 번스타인 — 시장 영향 분석"]
- disclaimer: "이 글은 특정 종목의 매수·매도를 권유하지 않으며, 투자 판단과 책임은 전적으로 투자자 본인에게 있습니다."

**a3 · 칼럼 · "시니어에게 AI는 날개가 된다"**
- section "오피니언 · 시니어", subtitle "AI를 이기려는 적이 아니라, 곁에서 돕는 동료로 두는 법"
- figCaption "개념도 — 두려움을 내려놓으면, 도구는 등에 날개가 된다"
- author: 박근필 / 칼럼니스트 · 수의사 / 이니셜 "박" / avatarBg `linear-gradient(135deg,#FF9F43,#8A4A0A)` / bio "나이 듦과 배움, 그리고 기술과 사람 사이의 태도에 관해 씁니다."
- date 2026.06.16, readTime 4분, rawViews 8420, rawLikes 289
- tags: 시니어, AI 활용, 디지털 문해, 태도
- theme: name COLUMN, chipBg `rgba(255,159,67,.2)`, chipCol `#FFC07A`, heroBase `radial-gradient(120% 130% at 15% 8%, #7A3B0A 0%, #3E1E06 44%, #120A05 78%)`, blobA `rgba(255,159,67,.9)`, blobB `rgba(232,18,60,.8)`, blobC `rgba(255,159,67,.55)`, ring `conic-gradient(from 0deg, #FF9F43, #E8123C, #FF9F43)`, relGrad `linear-gradient(135deg,#FF9F43,#8A4A0A)`, relCol `#FFC07A`
- blocks: p, p, q, h2("어떻게 쓰면 될까"), p, ul(3개), p, call("딱 하나만 기억하세요"), def
- ul items: ["모르는 단어의 뜻, 병원에서 들은 어려운 설명을 쉽게 풀어 달라 하기", "손주에게 줄 편지를 다정하게 다듬어 달라 하기", "오늘 본 영화의 줄거리와 감상을 정리해 달라 하기"]
- sources: 없음, disclaimer 없음
- 인용문(q): "걸어서 가야 했던 길을, 이제는 날아서 갈 수 있다." / 정의(def): "AI는 우리를 이기려는 적이 아니라, 두려움만 내려놓으면 등에 날개가 되어 주는 동료다."

> 참고: a1~a3 blocks의 모든 문단(p) 전문은 원본 `NEXUS_article_detail/logic.jsx`의 `data()` 배열에 있으며 재현 시 그대로 사용. 위 요약은 구조(블록 순서·타입·라벨·q/def 핵심 문장)를 명세한 것.

---

## 5. 반응형 (Responsive)

### 5.1 홈 앱 브레이크포인트
**`@media (max-width:860px)`**:
- `.topnav-links`, `.topnav-cta` 숨김 → `.burger`, `.mobnav` 표시.
- `.rgrid-4` → 2열, `.rgrid-3` → 2열, `.rgrid-2` → 1열.
- `.herowrap` → 1열, `.herocards` 숨김.
- `.pad` 좌우 패딩 18px, `.h1` 34px.
- `.detailgrid` → 1열 (클래스/밋플/결제 상세 단일 컬럼).
- `.appbody` 하단 패딩 74px (모바일 하단 네비 공간 확보).
- `.hidemob` 숨김 (검색창, 큐레이션 목록 카드 썸네일 등).

**`@media (max-width:560px)`**: `.rgrid-4` → 1열, `.rgrid-3` → 1열.

### 5.2 아티클 상세 앱 브레이크포인트
**`@media (max-width:860px)`**: topnav-links/hidemob 숨김, pad 18px, `.heroart` 360px, heroinner 패딩 축소, `.herotitle` 33px, `.herosub` 15.5px, `.keyvis` 220px, `.rgrid-2` 1열, `.metabar` wrap, `.metaright` 좌측정렬.

**`@media (max-width:560px)`**: `.heroart` auto/min 300px, `.herotitle` 27px/1.22, `.herosub` 14.5px, `.keyvis` 190px, `.stacklane` gap 96px, `.actionrow` wrap + `.actionspacer` 숨김, `.switcher` 축소 + swlabel 숨김, `.authorcard` 세로 스택.

---

## 6. 구현 우선순위 매핑

### 핵심 (Core — 1차 구현)
1. **홈 메인** (`home`) — 히어로 + 4개 섹션 + 전역 네비/푸터. 앱의 얼굴.
2. **큐레이션 목록** (`curation`) + **아티클 상세 앱** (섹션 4) — 콘텐츠 소비 핵심 경험. 애니메이션 키비주얼이 제품 차별점.
3. **전역 네비게이션 + 라우팅 상태 머신** — 모든 뷰의 뼈대.
4. **디자인 토큰 시스템** (색상/타이포/그라디언트) — 전 뷰 공유 기반.

### 보조 (Secondary — 2차 구현)
- **클래스 목록/상세** (`classes`, `class-detail`) — 카테고리 필터 + 커리큘럼 + 스티키 구매박스.
- **커뮤니티 목록/상세** (`community`, `community-detail`) — 댓글 입력/추가 상호작용.
- **밋플 목록/상세** (`meet`, `meet-detail`) — 이벤트 카드 + 타임라인.
- **AI핫딜** (`hotdeal`) — 블루 액센트, 외부 이미지 + 필터.
- **온보딩** (`onboarding`) — 3스텝 위저드.
- **결제** (`checkout`) — BC카드 UI + 완료 화면.
- **대시보드** (`dashboard`) — 진행률 + 통계 + 추천.

### 상호작용 요약 (구현 시 챙길 것)
- 카드 hover: `translateY(-4px)` + 레드 테두리.
- 카테고리/관심사 칩 활성 토글 (레드 배경).
- 아티클 좋아요/저장 토글 (likeCount +1), 유형 스위처 전환.
- 읽기 진행바 스크롤 동기화.
- 히어로/키비주얼 CSS 애니메이션 (heroMotion 프롭으로 on/off).
- 댓글 입력 → 리스트 추가, 온보딩 다단계 진행, 수강신청 → 결제 → 대시보드 플로우.
- 외부 링크: eat.pl(`web.paybooc.ai`), 핫딜 상품(`open.paybooc.co.kr`).
