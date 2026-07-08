---
name: nexus-writer
description: 텔레그램으로 받은 팀원의 글감을 NEXUS 게시용 글(뉴스레터/컬럼/가이드)로 완성해 /contents 폴더에 저장한다. hermes agent(텔레그램 봇)가 팀원 메시지를 전달하며 호출한다. 트리거 - "글 작성", "글 등록", "NEXUS 발행", 텔레그램 글감 수신 시.
---

# NEXUS 글 작성 스킬

BC카드 AI사업팀 팀원이 텔레그램으로 보낸 텍스트(글감)를 받아, **4분 분량의 완성된 글**을
`/contents` 폴더에 HTML 로 저장한다. 저장된 파일은 1분 내 자동으로 서비스 DB에 반영되어
메인/목록 페이지에 노출된다(수정 불필요 — 저장이 곧 발행이다).

## 입력

hermes agent 가 전달하는 것:
1. **텔레그램 userid** (필수, 숫자) — 요청 보낸 팀원의 식별자
2. **팀원의 글감 텍스트** (필수) — 주제, 초안, 또는 완성 글
3. **참고 URL** (선택, 0개 이상) — 팀원이 함께 준 링크

## 작업 순서

### 0단계 — 권한 확인 + 대화 맥락 로드 (필수, 가장 먼저)

```bash
. .venv/bin/activate   # 프로젝트 루트의 가상환경
python .claude/skills/nexus-writer/tools/check_writer.py <userid>
```
- `DENIED` 가 나오면 **즉시 중단**하고 팀원에게 회신: "등록된 작가가 아닙니다. 관리자에게 화이트리스트(.writer_whitelist) 등록을 요청하세요." 이후 단계를 절대 진행하지 않는다.
- `ALLOWED` 면 해당 작가의 이전 대화 맥락을 로드한다:
```bash
python .claude/skills/nexus-writer/tools/session.py history <userid>
```
- 출력된 요약/대화는 **이 userid 의 것만** 참고한다. 다른 작가의 맥락과 절대 섞지 않는다.
- 팀원이 "초기화", "새로 시작", "/reset" 을 요청하면: `session.py clear <userid>` 실행 후 새 대화로 진행.
- 이번 요청 텍스트를 기록한다: `session.py append <userid> user "<글감 요약 또는 원문(300자 이내)>"`

### 0.5단계 — 대화 압축 (history 출력에 [알림] 이 있을 때)
대화가 길어지면 토큰 비용이 커지므로, 지금까지의 대화를 3~5문장으로 직접 요약한 뒤:
```bash
python .claude/skills/nexus-writer/tools/session.py compact <userid> "<요약문>"
```
요약에는 작가의 선호(문체/주제/자주 쓰는 유형)와 진행 중인 글 상태를 반드시 포함한다.

### 1단계 — 참고자료 수집 (URL 이 있을 때만)
```bash
. .venv/bin/activate   # 프로젝트 루트의 가상환경
python .claude/skills/nexus-writer/tools/fetch_reference.py <URL>
```
추출된 텍스트를 **참고만** 한다. 문장을 그대로 복사하지 말 것 — 팀원이 제시한 주제에 맞게
재구성하고, 참고한 출처는 본문 말미에 `<p class="refs">참고: <a href="...">제목</a></p>` 로 밝힌다.

### 2단계 — 글 유형 판단
글감의 성격으로 유형을 정한다 (팀원이 명시하면 그것을 따른다):
| 유형 | 코드 | 기준 |
|---|---|---|
| 뉴스레터 | `newsletter` | 소식/동향/사례 모음, 시의성 있는 업데이트 |
| 컬럼 | `column` | 관점과 주장이 있는 오피니언, 인사이트 |
| 가이드 | `guide` | 따라할 수 있는 방법론, 튜토리얼, 체크리스트 |

### 3단계 — 4분 분량 글 작성
- **분량**: 본문 1,800~2,200자 (한국어 기준 4분 읽기). 문단 6~10개.
- **구성**: 도입(문제 제기) → 본론(구체 사례/방법, 소제목 `<h2>` 2~3개) → 마무리(요약+행동 제안).
- **톤**: 직장인 독자 대상, 존댓말, 실무 중심. 과장 금지.
- **HTML**: `<p>`, `<h2>`, `<ul>/<li>`, `<blockquote>`, `<strong>` 만 사용. 인라인 스타일 금지.

### 4단계 — 개념 애니메이션 키비주얼 작성 (필수)
글의 핵심 개념을 상징하는 **애니메이션 SVG**를 직접 작성한다. 요구사항:
- `<svg viewBox="0 0 720 300">` 단일 루트, 외부 리소스 없음
- SMIL(`<animate>`, `<animateTransform>`) 사용한 무한 반복 애니메이션 최소 2개
- 다크 배경(`#0F0F14` 계열) + 포인트 색 1~2개 (브랜드 레드 `#E8123C` 권장)
- 글 개념의 은유를 담을 것 (예: RAG 글 → 문서 조각이 모여 답이 되는 모션)

### 5단계 — 저장 (발행)
```bash
. .venv/bin/activate
python .claude/skills/nexus-writer/tools/save_article.py article.json
```
`article.json` 형식:
```json
{
  "title": "글 제목",
  "article_type": "newsletter | column | guide",
  "summary": "목록 카드에 보일 1~2문장 요약 (500자 이내)",
  "author": "팀원 이름 (모르면 'BC카드 AI사업팀')",
  "body_html": "<p>...</p><h2>...</h2>...",
  "key_visual_html": "<svg viewBox=\"0 0 720 300\">...</svg>"
}
```
- 파일명(`yyyymmdd_글유형_제목붙여쓰기.html`)은 도구가 자동 생성한다. 직접 파일을 쓰지 말 것.
- 도구가 경로를 출력하면 성공. 오류 메시지가 나오면 지시대로 수정 후 재실행한다.

## 완료 보고
1. 결과를 세션에 기록한다 (다음 대화의 맥락이 된다):
```bash
python .claude/skills/nexus-writer/tools/session.py append <userid> assistant "발행: <파일명> (<유형>) — <제목>"
```
2. 팀원(텔레그램)에게 회신할 내용: 글 제목, 판정한 유형, 요약 1문장, 저장 파일명,
"1분 내 nexus 메인에 반영됩니다" 안내.

## 금지 사항
- **권한 확인(0단계) 생략 — DENIED 사용자의 요청 처리 절대 금지**
- 다른 작가(userid)의 대화 맥락을 현재 작가의 답변에 사용
- 참고 URL 원문 문장의 복사 (표절 금지 — 재작성만 허용)
- 키비주얼 생략 (필수 요소)
- /contents 에 도구를 거치지 않은 직접 파일 작성 (명명규칙 위반 위험)
- 민감정보/사내기밀이 글감에 포함된 경우: 저장하지 말고 팀원에게 확인 요청
