"""수집형 클래스 목록 API 테스트."""
from app.models import Course


def add_course(client, source_id, category, badges, rank=1, status="published"):
    names = {
        "DATASCIENCEDL": "AI TECH",
        "AICREATIVE": "AI CREATIVE",
        "BIZ": "AI/업무생산성",
        "DAKER": "해커톤",
        "DACON": "경진대회",
    }
    source_type = {
        "DAKER": "daker",
        "DACON": "dacon",
    }.get(category, "fastcampus")
    db = client.session_factory()
    db.add(Course(
        source_type=source_type, source_id=source_id,
        source_category_code=category, source_category_name=names[category],
        source_category_url=f"https://fastcampus.co.kr/category_online_{category.lower()}",
        source_rank=rank, title=f"과정 {source_id}", summary="설명",
        source_url=f"https://fastcampus.co.kr/{source_id}",
        thumbnail_url=f"https://cdn.example/{source_id}.webp",
        sub_category_name="AI 생산성", format_name="올인원", qualification="누구나",
        running_time_minutes=600, sale_price=200000, list_price=400000,
        badges="|".join(badges), status=status,
    ))
    db.commit()
    db.close()


def test_classes_api_lists_only_published_with_external_ref(client):
    add_course(client, "1", "DATASCIENCEDL", ["BEST", "NEW"])
    add_course(client, "2", "AICREATIVE", ["NEW"], status="hidden")
    res = client.get("/api/classes?page=1&size=20")
    assert res.status_code == 200
    body = res.json()
    assert body["meta"]["total"] == 1
    item = body["data"][0]
    assert item["title"] == "과정 1"
    assert item["badges"] == ["BEST", "NEW"]
    assert item["linkUrl"].endswith("?ref=nexus.bccard.ai")
    assert item["isExternal"] is True


def test_classes_api_filters_by_source_category(client):
    add_course(client, "1", "DATASCIENCEDL", ["BEST"])
    add_course(client, "2", "AICREATIVE", ["NEW"])
    add_course(client, "3", "BIZ", ["얼리버드"])
    res = client.get("/api/classes?category=AICREATIVE&page=1&size=20")
    assert res.status_code == 200
    assert [x["sourceId"] for x in res.json()["data"]] == ["2"]
    assert res.json()["meta"]["total"] == 1


def test_classes_api_lists_opportunity_categories_with_source_type(client):
    add_course(client, "daker:1", "DAKER", ["모집중"])
    add_course(client, "dacon:2", "DACON", ["참가신청중"])

    daker = client.get("/api/classes?category=DAKER").json()
    dacon = client.get("/api/classes?category=DACON").json()

    assert daker["data"][0]["sourceType"] == "daker"
    assert daker["data"][0]["sourceCategoryName"] == "해커톤"
    assert dacon["data"][0]["sourceType"] == "dacon"
    assert dacon["data"][0]["sourceCategoryName"] == "경진대회"


def test_classes_api_orders_by_rank_first_across_categories(client):
    """전체 목록은 source_rank 우선 정렬 — 각 카테고리 1위들이 섞여 상단에 온다.

    (홈 '지금 뜨는 클래스'가 한 카테고리 상위권으로 고정되지 않게 하는 기준.
    rank 동률은 카테고리 우선순위: DATASCIENCEDL → AICREATIVE → BIZ → DAKER → DACON)"""
    add_course(client, "ds-1", "DATASCIENCEDL", ["BEST"], rank=1)
    add_course(client, "ds-2", "DATASCIENCEDL", ["NEW"], rank=2)
    add_course(client, "cr-1", "AICREATIVE", ["NEW"], rank=1)
    add_course(client, "biz-1", "BIZ", ["얼리버드"], rank=1)
    add_course(client, "daker:1", "DAKER", ["모집중"], rank=1)

    res = client.get("/api/classes?page=1&size=4")

    assert [x["sourceId"] for x in res.json()["data"]] == [
        "ds-1", "cr-1", "biz-1", "daker:1",
    ]


def test_classes_api_pushes_nonpositive_rank_to_back(client):
    """rank 는 관례상 1부터지만, 0 이하 행이 생겨도 전체 상단을 장악하지 못하게 뒤로 보낸다."""
    add_course(client, "ds-1", "DATASCIENCEDL", ["BEST"], rank=1)
    add_course(client, "broken", "AICREATIVE", ["NEW"], rank=0)

    res = client.get("/api/classes?page=1&size=10")

    assert [x["sourceId"] for x in res.json()["data"]] == ["ds-1", "broken"]


def test_classes_api_category_filter_keeps_rank_order(client):
    add_course(client, "ds-2", "DATASCIENCEDL", ["NEW"], rank=2)
    add_course(client, "ds-1", "DATASCIENCEDL", ["BEST"], rank=1)

    res = client.get("/api/classes?category=DATASCIENCEDL")

    assert [x["sourceId"] for x in res.json()["data"]] == ["ds-1", "ds-2"]


def test_classes_api_rejects_unknown_category(client):
    assert client.get("/api/classes?category=UNKNOWN").status_code == 422
