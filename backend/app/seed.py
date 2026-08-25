"""초기 데이터 시드: 메뉴 카테고리 5개 + 샘플 큐레이션 글 6개 (docs/DESIGN_SPEC.md §3).

실행: python -m app.seed  (테이블 생성 포함, 멱등)
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Article, Base, Category

CATEGORIES = [
    ("curation", "큐레이션", "매일 업데이트되는 AI 테크 강좌와 금융·커리어 인사이트. 출근길에 한 편씩.", 1),
    ("class", "클래스", "BC카드 데이터로 배우는 온라인·오프라인 강의. 직장인도 개발자도, 실무에 바로 씁니다.", 2),
    ("community", "커뮤니티", "팁·기술자료·삽질 후기까지. 현직자들이 직접 등록하고 댓글로 나눕니다.", 3),
    ("meetpl", "meet.pl", "밋업·세미나·해커톤 소식을 한곳에서. 관심 있는 이벤트에 참가 신청하세요.", 4),
    ("hotdeal", "AI핫딜", "gemma 27B 추천 — 데이터: open.paybooc.co.kr/bcai · BC카드 AI 핫픽 API", 5),
]

BODY_PARAGRAPHS = (
    "<p>많은 조직이 생성형 AI 도입을 검토하지만, 정작 가장 큰 장벽은 모델 성능이 아니라 데이터 거버넌스와 신뢰성입니다.</p>"
    "<p>특히 금융처럼 규제가 강한 산업에서는 \"왜 이 답이 나왔는가\"를 설명할 수 있어야 하고, 민감 정보가 새지 않도록 가드레일을 촘촘히 세워야 합니다.</p>"
    "<p>실무에서는 작은 범위의 내부 업무(문서 검색, 요약, 초안 작성)부터 시작해 점진적으로 확장하는 전략이 가장 안전합니다.</p>"
    "<p>EDU.AI 클래스에서는 이 과정을 BC카드의 실제 익명 데이터로 직접 실습하며, 도입 의사결정에 필요한 감각을 기릅니다.</p>"
)

SAMPLE_ARTICLES = [
    ("column", "GPT-5 시대, 금융권은 LLM을 어떻게 도입하고 있나", "EDU.AI 에디터", 7,
     "규제 산업인 금융에서 생성형 AI를 실서비스에 올리기까지, 국내 주요 금융사들의 도입 전략과 거버넌스를 정리했습니다.", "#FF1E4E"),
    ("guide", "비전공 직장인이 6개월 만에 데이터 분석가로 이직한 법", "커리어 인사이트", 5,
     "엑셀만 쓰던 마케터가 SQL과 파이썬을 익히고 데이터 직무로 전환하기까지의 현실적인 학습 로드맵.", "#7A5CFF"),
    ("column", "RAG vs 파인튜닝, 우리 회사엔 뭐가 맞을까", "EDU.AI 에디터", 8,
     "비용·정확도·유지보수 관점에서 두 접근을 비교하고, 사내 도입 시 의사결정 체크리스트를 제시합니다.", "#00B8A9"),
    ("newsletter", "결제 데이터로 보는 2026 상반기 소비 트렌드", "데이터 리포트", 6,
     "BC카드 익명 통계로 본 세대별 소비 변화. 여행·구독·식품 카테고리에서 두드러진 시그널을 짚어봅니다.", "#FFB020"),
    ("column", "AI 에이전트가 바꾸는 백오피스 업무", "비즈니스 인사이트", 5,
     "정산·리포팅·고객 응대까지, 에이전트가 실제로 대체하기 시작한 업무와 사람이 남겨야 할 일.", "#2D9CDB"),
    ("guide", "주니어 개발자가 알아야 할 MLOps 기본기", "EDU.AI 에디터", 9,
     "모델을 만드는 것과 운영하는 것은 다른 문제입니다. 실험 관리부터 배포 파이프라인까지 최소 지식 정리.", "#E8123C"),
]


def key_visual_svg(accent: str, label: str) -> str:
    """개념 애니메이션 키비주얼 (샘플 글용 SVG)."""
    return (
        f'<svg viewBox="0 0 720 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{label}">'
        f'<rect width="720" height="300" fill="#0F0F14"/>'
        f'<circle cx="360" cy="150" r="70" fill="none" stroke="{accent}" stroke-width="2" opacity="0.9">'
        f'<animate attributeName="r" values="60;80;60" dur="4s" repeatCount="indefinite"/>'
        f"</circle>"
        f'<circle cx="360" cy="150" r="34" fill="{accent}">'
        f'<animate attributeName="opacity" values="0.75;1;0.75" dur="2.6s" repeatCount="indefinite"/>'
        f"</circle>"
        f'<text x="360" y="262" text-anchor="middle" font-family="monospace" font-size="13" fill="#8b8b95" letter-spacing="3">{label}</text>'
        f"</svg>"
    )


def seed_categories(db: Session) -> dict[str, Category]:
    existing = {c.slug: c for c in db.scalars(select(Category))}
    for slug, name, description, order in CATEGORIES:
        if slug not in existing:
            category = Category(slug=slug, name=name, description=description, display_order=order)
            db.add(category)
            existing[slug] = category
    db.commit()
    return existing


def seed_sample_articles(db: Session, curation: Category) -> int:
    existing_titles = set(db.scalars(select(Article.title)))
    created = 0
    for index, (atype, title, source, minutes, excerpt, accent) in enumerate(SAMPLE_ARTICLES):
        if title in existing_titles:
            continue
        db.add(
            Article(
                category_id=curation.id,
                article_type=atype,
                title=title,
                summary=excerpt,
                body_html=BODY_PARAGRAPHS,
                key_visual_html=key_visual_svg(accent, f"EDU.AI · {source}"),
                author_name=source,
                source_type="internal",
                read_minutes=minutes,
                published_at=datetime(2026, 7, 1 + index, 9, 0, tzinfo=timezone.utc),
            )
        )
        created += 1
    db.commit()
    return created


SAMPLE_POSTS = [
    ("데브워커", "노하우", "사내에서 RAG 도입한 후기 (삽질 포함)", 218,
     "규정 문서가 수천 페이지라 검색이 지옥이었는데, RAG 붙이고 나서 문의량이 절반으로 줄었습니다. 다만 청킹 전략을 잘못 잡아서 처음엔 엉뚱한 답이 많이 나왔어요. 결국 문서 구조 기반으로 청크를 나누니 정확도가 확 올랐습니다.",
     [("러너A", "청킹 전략 좀 더 자세히 알 수 있을까요?"),
      ("데브워커", "문서 H2 헤딩 단위로 잘랐어요. 곧 글로 정리할게요!"),
      ("호기심", "문의량 절반 ㄷㄷ 사내 설득 자료로 써도 될까요")]),
    ("GPU장인", "기술자료", "gemma 27B 로컬 구동 스펙 정리해봤어요", 312,
     "질문이 많아서 정리합니다. 양자화(4bit) 기준 VRAM 20GB 정도면 무난하게 돌아갑니다. 3090/4090 한 장으로 충분하고, 추론 속도는 토큰당 대략...",
     [("초보", "4bit면 품질 손해 많이 보나요?"),
      ("GPU장인", "체감상 거의 없습니다. 일반 업무용은 충분해요.")]),
    ("입문러", "노하우", "비전공자도 파인튜닝 해봤습니다", 156,
     "문과 출신 기획자입니다. EDU.AI LLM 클래스 듣고 처음으로 LoRA 파인튜닝까지 해봤는데, 생각보다 진입장벽이 낮았어요. 데이터셋 만드는 게 제일 오래 걸렸습니다.",
     [("EDU.AI", "좋은 글 감사합니다 👏")]),
    ("직장인K", "팁", "엑셀 대신 파이썬으로 월말 정산 자동화한 썰", 421,
     "매달 3일씩 걸리던 정산을 pandas로 자동화했더니 10분이면 끝납니다. 처음엔 무서웠는데 클래스에서 배운 대로 차근차근 하니 됐어요. 코드 공유합니다.",
     [("정산러", "코드 감사합니다 ㅠㅠ 바로 적용했어요"),
      ("직장인K", "도움 됐다니 다행입니다!")]),
    ("프롬프트수집가", "자료", "프롬프트 템플릿 모음 공유합니다", 689,
     "업무별로 자주 쓰는 프롬프트를 정리했습니다. 회의록 요약, 이메일 초안, 데이터 해석 요청 등 바로 복붙해서 쓰세요.",
     [("EDU.AI", "좋은 글 감사합니다 👏")]),
]


def seed_sample_posts(db: Session) -> int:
    """디자인 시안(§3.4)의 커뮤니티 샘플 글/댓글 시드 (멱등)."""
    from app.models import CommunityComment, CommunityPost

    existing_titles = set(db.scalars(select(CommunityPost.title)))
    created = 0
    for index, (author, tag, title, likes, body, comments) in enumerate(SAMPLE_POSTS):
        if title in existing_titles:
            continue
        post = CommunityPost(
            author_name=author, tag=tag, title=title, body=body,
            likes_count=likes, comments_count=len(comments),
            created_at=datetime(2026, 7, 1 + index, 12, 0, tzinfo=timezone.utc),
        )
        db.add(post)
        db.flush()
        for c_author, c_body in comments:
            db.add(CommunityComment(post_id=post.id, author_name=c_author, body=c_body))
        created += 1
    db.commit()
    return created


def seed_all(db: Session) -> None:
    categories = seed_categories(db)
    seed_sample_articles(db, categories["curation"])
    seed_sample_posts(db)


def main() -> None:
    from app.db import get_engine

    engine = get_engine()
    Base.metadata.create_all(engine)
    with Session(bind=engine) as db:
        seed_all(db)
    print("시드 완료: 카테고리/샘플 글 반영")


if __name__ == "__main__":
    main()
