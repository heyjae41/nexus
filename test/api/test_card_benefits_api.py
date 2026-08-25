"""Card.Pick 카드 혜택 공개 API 테스트.

응답 JSON 은 다른 채널도 그대로 소비하므로 DB 필수 컬럼명(snake_case)을
그대로 포함해야 한다: title, event_period, card_company, target_cards,
detail_url, image_url.
"""
from datetime import date, timedelta

from app.models import CardBenefit

REQUIRED_KEYS = {
    "title", "event_period", "card_company", "target_cards", "detail_url", "image_url",
}


def seed_benefits(client, count=3):
    db = client.session_factory()
    for i in range(count):
        db.add(
            CardBenefit(
                source_id=f"hana:{i}",
                card_company="하나카드" if i % 2 == 0 else "우리카드",
                title=f"여행 혜택 {i}",
                event_period=f"2026.08.0{i + 1} ~ 2026.09.30",
                event_start_date=date(2026, 8, i + 1),
                event_end_date=date(2026, 9, 30),
                target_cards="전 카드",
                benefit_summary=f"여행 혜택 {i} 요약 — 최대 {i + 1}만원 할인",
                benefit_tags="할인,캐시백",
                detail_url=f"https://m.hanacard.co.kr/MKEVT1010M.web?EVN_SEQ={i}",
                image_url=f"https://m.hanacard.co.kr/img{i}.png",
            )
        )
    db.commit()
    db.close()


def test_card_benefits_returns_required_columns(client):
    seed_benefits(client)
    res = client.get("/api/card-benefits")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert len(body["data"]) == 3
    item = body["data"][0]
    assert REQUIRED_KEYS <= set(item.keys()), "필수 컬럼명이 JSON 에 그대로 있어야 한다"
    # 최신 시작일이 먼저 (published 최신순과 동일한 규칙)
    assert item["title"] == "여행 혜택 2"
    # 수집 콘텐츠 이동 URL 규칙: ref 부착
    assert item["detail_url"].endswith("ref=nexus.bccard.ai")
    assert "EVN_SEQ=2" in item["detail_url"]
    assert item["card_company"] == "하나카드"
    assert item["event_period"] == "2026.08.03 ~ 2026.09.30"
    assert item["image_url"] == "https://m.hanacard.co.kr/img2.png"
    # 이벤트 혜택 요약도 API 항목으로 내린다 (목록 카드 제목 아래 노출용)
    assert item["benefit_summary"] == "여행 혜택 2 요약 — 최대 3만원 할인"


def test_card_benefits_filter_by_company(client):
    seed_benefits(client)
    res = client.get("/api/card-benefits?company=우리카드")
    body = res.json()
    assert body["success"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["card_company"] == "우리카드"


def test_card_benefits_excludes_ended_events(client):
    """종료된(어제까지) 이벤트는 기본 노출에서 제외한다."""
    db = client.session_factory()
    db.add(
        CardBenefit(
            source_id="hana:old", card_company="하나카드", title="지난 혜택",
            event_period="2026.01.01 ~ 2026.01.31",
            event_start_date=date(2026, 1, 1),
            event_end_date=date.today() - timedelta(days=1),
            detail_url="https://m.hanacard.co.kr/MKEVT1010M.web?EVN_SEQ=old",
        )
    )
    db.commit()
    db.close()

    res = client.get("/api/card-benefits")
    titles = [x["title"] for x in res.json()["data"]]
    assert "지난 혜택" not in titles


def test_card_benefits_cached_until_version_bump(client):
    seed_benefits(client, count=1)
    first = client.get("/api/card-benefits").json()
    assert len(first["data"]) == 1

    # 캐시 무효화 없이 직접 DB 추가 → 캐시 히트로 그대로
    db = client.session_factory()
    db.add(CardBenefit(
        source_id="woori:new", card_company="우리카드", title="새 혜택",
        event_period="2026.08.01 ~", event_start_date=date(2026, 8, 1),
        detail_url="https://m.wooricard.com/d?evntSrno=new",
    ))
    db.commit()
    db.close()
    assert len(client.get("/api/card-benefits").json()["data"]) == 1

    client.cache.bump_version()
    assert len(client.get("/api/card-benefits").json()["data"]) == 2


def test_card_benefits_excludes_not_started_events(client):
    """시작일이 미래인 이벤트는 '진행 중'이 아니므로 노출하지 않는다."""
    db = client.session_factory()
    db.add(
        CardBenefit(
            source_id="hana:future", card_company="하나카드", title="다음달 혜택",
            event_period="미래", event_start_date=date.today() + timedelta(days=10),
            event_end_date=date.today() + timedelta(days=40),
            detail_url="https://m.hanacard.co.kr/MKEVT1010M.web?EVN_SEQ=future",
        )
    )
    db.commit()
    db.close()

    res = client.get("/api/card-benefits")
    titles = [x["title"] for x in res.json()["data"]]
    assert "다음달 혜택" not in titles


def seed_geo_benefits(client):
    db = client.session_factory()
    rows = [
        ("bc:vn", "베트남 다낭 호텔 25% 할인", "VN", "2026.08.01"),
        ("bc:sea", "동남아 전 가맹점 5% 할인", "동남아", "2026.08.02"),
        ("bc:jp", "일본 편의점 적립", "JP", "2026.08.03"),
        ("bc:ov", "해외 결제 캐시백", "ALL", "2026.08.04"),
        ("bc:de", "독일 여행 할인", "독일", "2026.08.05"),
    ]
    for sid, title, countries, start in rows:
        db.add(CardBenefit(
            source_id=sid, card_company="BC카드", title=title,
            event_period=f"{start} ~ 2026.12.31",
            event_start_date=date(*map(int, start.split("."))),
            event_end_date=date(2026, 12, 31),
            countries=countries, detail_url=f"https://ex.com/{sid}",
        ))
    db.commit()
    db.close()


def test_card_benefits_country_filter_uses_code_and_all(client):
    """VN 선택 = VN 명시 ∪ ALL, 명시 우선 정렬."""
    seed_geo_benefits(client)
    res = client.get("/api/card-benefits", params={"country": "VN"})
    data = res.json()["data"]
    titles = [x["title"] for x in data]
    assert "베트남 다낭 호텔 25% 할인" in titles
    assert "동남아 전 가맹점 5% 할인" in titles
    assert "해외 결제 캐시백" in titles
    assert "일본 편의점 적립" not in titles
    assert "동남아 전 가맹점 5% 할인" in titles  # 기존 권역값은 ALL로 정규화
    # 명시(VN) → 해외공통 순
    assert titles[0] == "베트남 다낭 호텔 25% 할인"
    assert all(item["geo_match"] == "common" for item in data[1:])


def test_card_benefits_country_meta_and_field(client):
    seed_geo_benefits(client)
    res = client.get("/api/card-benefits")
    body = res.json()
    assert body["data"][0]["countries"]  # 지역 필드 포함 (리스트)
    assert isinstance(body["data"][0]["countries"], list)
    # 국가 칩은 코드로 식별하고, 표시명은 별도 메타데이터로 제공한다.
    places = {p["code"]: p for p in body["meta"]["countries"]}
    # 국가 칩 건수는 국가 명시 혜택만, ALL 칩은 해외공통 혜택 수다.
    assert places["VN"] == {"code": "VN", "name": "베트남", "flag": "🇻🇳", "count": 1}
    assert places["JP"]["count"] == 1
    assert places["ALL"]["count"] == 3


def test_card_benefits_invalid_country_rejected(client):
    seed_geo_benefits(client)
    res = client.get("/api/card-benefits", params={"country": "없는나라"})
    assert res.status_code == 400


def test_card_benefits_country_filter_marks_geo_match(client):
    """country 지정 시 각 항목에 매칭 유형(geo_match)을 표시한다 — 프론트가
    '특화 혜택'과 '해외 공통 혜택' 섹션을 시각적으로 나누는 데 쓴다."""
    seed_geo_benefits(client)
    res = client.get("/api/card-benefits", params={"country": "VN"})
    data = res.json()["data"]
    by_title = {x["title"]: x.get("geo_match") for x in data}
    assert by_title["베트남 다낭 호텔 25% 할인"] == "exact"
    assert by_title["동남아 전 가맹점 5% 할인"] == "common"
    assert by_title["해외 결제 캐시백"] == "common"
    # country 미지정 시엔 geo_match 없음
    res_all = client.get("/api/card-benefits")
    assert all("geo_match" not in x for x in res_all.json()["data"])
