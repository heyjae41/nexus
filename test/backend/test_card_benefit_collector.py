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
    assert rows["hana:jp"].countries == "일본"
    assert set(rows["hana:sea"].countries.split(",")) == {"동남아", "베트남", "태국"}
    assert rows["hana:ov"].countries == "해외공통"
    assert rows["hana:dom"].countries == "국내·기타"
