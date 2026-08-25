"""Card.Pick 수집기 — DB 반영/중복/캐시 무효화 테스트."""
from datetime import date

from app.models import CardBenefit
from app.services.card_benefit_collector import collect_card_benefits
from app.services.card_benefit_fetcher import CardBenefitCandidate

from shared import make_cache  # noqa: E402 — 수집 테스트 공용 헬퍼


def make_candidate(**over):
    base = dict(
        source_id="hana:60480",
        card_company="하나카드",
        title="해외 결제하면 최대 10만 하나머니!",
        event_period="2026.08.01 ~ 2026.09.30",
        event_start_date=date(2026, 8, 1),
        event_end_date=date(2026, 9, 30),
        target_cards="JADE 카드",
        benefit_summary="해외 결제 시 최대 10만 하나머니 적립",
        benefit_tags="적립",
        detail_url="https://m.hanacard.co.kr/MKEVT1010M.web?EVN_SEQ=60480",
        image_url="https://m.hanacard.co.kr/a.png",
    )
    base.update(over)
    return CardBenefitCandidate(**base)


def test_collect_saves_new_benefits(db):
    cache = make_cache()
    result = collect_card_benefits(
        db, cache,
        candidates=[make_candidate(), make_candidate(source_id="woori:1", card_company="우리카드",
                                                     detail_url="https://m.wooricard.com/d?evntSrno=1")],
    )

    assert result.candidates == 2
    assert result.added == 2
    rows = db.query(CardBenefit).all()
    assert {r.card_company for r in rows} == {"하나카드", "우리카드"}
    saved = next(r for r in rows if r.card_company == "하나카드")
    assert saved.title == "해외 결제하면 최대 10만 하나머니!"
    assert saved.event_period == "2026.08.01 ~ 2026.09.30"
    assert saved.target_cards == "JADE 카드"
    assert saved.benefit_summary == "해외 결제 시 최대 10만 하나머니 적립"
    assert saved.detail_url == "https://m.hanacard.co.kr/MKEVT1010M.web?EVN_SEQ=60480"
    assert saved.image_url == "https://m.hanacard.co.kr/a.png"


def test_collect_skips_existing_by_source_id_and_url(db):
    cache = make_cache()
    collect_card_benefits(db, cache, candidates=[make_candidate()])

    again = collect_card_benefits(db, cache, candidates=[
        make_candidate(),  # 완전 중복
        make_candidate(source_id="hana:9999"),  # detail_url 중복
    ])

    assert again.added == 0
    assert db.query(CardBenefit).count() == 1


def test_collect_bumps_cache_only_when_added(db):
    cache = make_cache()
    cache.set("cardpick", "stale")
    collect_card_benefits(db, cache, candidates=[make_candidate()])
    assert cache.get("cardpick") is None, "신규 반영 시 캐시 무효화"

    cache.set("cardpick", "warm")
    collect_card_benefits(db, cache, candidates=[make_candidate()])
    assert cache.get("cardpick") == "warm", "변화 없으면 캐시 유지"


def test_collect_updates_period_and_image_on_change(db):
    """동일 이벤트(source_id)의 기간/이미지/대상카드 변경은 갱신한다."""
    cache = make_cache()
    collect_card_benefits(db, cache, candidates=[make_candidate()])

    changed = make_candidate(
        event_period="2026.08.01 ~ 2026.10.31",
        event_end_date=date(2026, 10, 31),
        target_cards="JADE, MULTI 카드",
        benefit_summary="연장! 최대 20만 하나머니 적립",
        image_url="https://m.hanacard.co.kr/b.png",
    )
    result = collect_card_benefits(db, cache, candidates=[changed])

    assert result.added == 0
    assert result.updated == 1
    row = db.query(CardBenefit).one()
    assert row.event_period == "2026.08.01 ~ 2026.10.31"
    assert row.target_cards == "JADE, MULTI 카드"
    assert row.benefit_summary == "연장! 최대 20만 하나머니 적립"
    assert row.image_url == "https://m.hanacard.co.kr/b.png"


def test_collect_fills_missing_dates_with_defaults(db):
    """날짜 정보가 없으면 시작=수집일, 종료=당해년도 12월 31일로 채운다."""
    from datetime import date as date_cls

    cache = make_cache()
    no_dates = make_candidate(
        source_id="hana:nodate", detail_url="https://ex.com/nodate",
        event_period="", event_start_date=None, event_end_date=None,
    )
    collect_card_benefits(db, cache, candidates=[no_dates])

    row = db.query(CardBenefit).filter_by(source_id="hana:nodate").one()
    today = date_cls.today()
    assert row.event_start_date == today
    assert row.event_end_date == date_cls(today.year, 12, 31)
    # 표시용 기간 문자열도 기본값으로 구성된다
    assert row.event_period == (
        f"{today.strftime('%Y.%m.%d')} ~ {today.year}.12.31"
    )


def test_collect_keeps_existing_dates(db):
    """날짜가 있으면 기본값을 덮어쓰지 않는다."""
    cache = make_cache()
    collect_card_benefits(db, cache, candidates=[make_candidate()])
    row = db.query(CardBenefit).one()
    assert row.event_start_date == date(2026, 8, 1)
    assert row.event_period == "2026.08.01 ~ 2026.09.30"


def test_collect_extracts_countries(db):
    """수집 시 제목·요약·대상 텍스트에서 대상 지역을 분류해 저장한다."""
    cache = make_cache()
    collect_card_benefits(db, cache, candidates=[
        make_candidate(source_id="hana:jp", detail_url="https://ex.com/jp",
                       title="일본 세븐일레븐 결제 시 적립"),
        make_candidate(source_id="hana:sea", detail_url="https://ex.com/sea",
                       title="동남아 여행 특가", benefit_summary="다낭·방콕 호텔 할인"),
        make_candidate(source_id="hana:ov", detail_url="https://ex.com/ov",
                       title="해외 결제 캐시백", benefit_summary=None),
        make_candidate(source_id="hana:dom", detail_url="https://ex.com/dom",
                       title="서울랜드 이용권", benefit_summary=None),
    ])
    rows = {r.source_id: r for r in db.query(CardBenefit).all()}
    assert rows["hana:jp"].countries == "JP"
    assert set(rows["hana:sea"].countries.split(",")) == {"VN", "TH"}
    assert rows["hana:ov"].countries == "ALL"
    assert rows["hana:dom"].countries == "ALL"


def test_collect_uses_detail_geo_text_for_countries(db):
    """v2: 제목·요약에 지역 단서가 없어도 상세 전문(geo_text)으로 분류한다."""
    cache = make_cache()
    collect_card_benefits(db, cache, candidates=[
        make_candidate(
            source_id="kb:v2", detail_url="https://ex.com/v2",
            title="여름 특별 이벤트",            # 지역 단서 없음
            benefit_summary="최대 5만원 할인",   # 지역 단서 없음
            target_cards=None,
            geo_text="다낭·나트랑 직항 항공권 결제 시 적용됩니다",  # 상세 전문
        ),
        make_candidate(
            source_id="kb:v2ov", detail_url="https://ex.com/v2ov",
            title="여름 특별 이벤트", benefit_summary="최대 5만원 할인",
            target_cards=None,
            geo_text="해외 이용 시 별도 수수료가 부과됩니다",  # 유의사항 상용구
        ),
        make_candidate(
            source_id="kb:v2fp", detail_url="https://ex.com/v2fp",
            title="제휴 브랜드 할인", benefit_summary=None, target_cards=None,
            geo_text="파리바게뜨·런던제화 매장, 세부 일정은 영문(로마자) 안내 참조",
        ),
    ])
    rows = {r.source_id: r for r in db.query(CardBenefit).all()}
    assert rows["kb:v2"].countries == "VN"
    # geo_text(본문)의 '해외' 상용구는 해외공통 신호로 쓰지 않는다 —
    # 국내 이벤트 유의사항("해외 이용 시 제외/수수료")의 오탐을 막기 위함
    assert rows["kb:v2ov"].countries == "ALL"
    # 파리바게뜨/런던제화/세부 일정/로마자 는 지역이 아니다 (오탐 가드)
    assert rows["kb:v2fp"].countries == "ALL"
