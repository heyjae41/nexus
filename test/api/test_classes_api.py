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


def test_classes_api_rejects_unknown_category(client):
    assert client.get("/api/classes?category=UNKNOWN").status_code == 422
