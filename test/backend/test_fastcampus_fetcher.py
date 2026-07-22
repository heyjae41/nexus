"""패스트캠퍼스 클래스 공개 JSON API 수집기 테스트."""
from app.services.fastcampus_fetcher import (
    FastCampusSource,
    fetch_fastcampus_candidates,
)


class Response:
    def __init__(self, data, status=200):
        self.data = data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError("failed", request=None, response=None)

    def json(self):
        return self.data


class Client:
    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = []

    def get(self, url, params=None):
        self.calls.append((url, params))
        key = url if params is None else (url, tuple(sorted(params.items())))
        return Response(self.payloads[key])


def course(cid, slug, title, highlight=""):
    return {
        "id": cid,
        "slug": slug,
        "state": "ONGOING",
        "publicTitle": title,
        "publicDescription": f"{title} 설명",
        "qualification": "누구나",
        "runningTime": "12:30",
        "desktopCardAsset": f"https://cdn.example/{cid}.webp",
        "category": {"title": "AI TECH"},
        "subCategory": {"title": "RAG & AI Agent"},
        "format": {"title": "올인원"},
        "cardInfo": {
            "standardBadgeTitle": "온라인",
            "highlightBadgeTitle": highlight,
        },
    }


def test_fetch_selects_only_target_badges_and_maps_products():
    base = "https://fastcampus.co.kr"
    source = FastCampusSource(
        page_url=f"{base}/category_online_datasciencedl",
        code="DATASCIENCEDL",
        label="AI TECH",
    )
    category_url = f"{base}/.api/categories/DATASCIENCEDL"
    best_url = f"{base}/.api/courses/recommended/best"
    latest_url = f"{base}/.api/courses/marketing/latest"
    product_url = f"{base}/.api/courses/products"
    client = Client({
        category_url: {"data": {"id": 39, "courses": [
            course(1, "popular", "인기 강의", "인기 급상승"),
            course(2, "best", "베스트 강의"),
            course(3, "new", "신규 강의"),
            course(4, "ordinary", "일반 강의"),
        ]}},
        best_url: {"data": {"39": [2]}},
        latest_url: {"data": {"39": [3]}},
        (product_url, (("id", "1,2,3"),)): {"data": {
            "1": [{"state": "NORMAL", "isPurchasable": True, "salePrice": 220000, "listPrice": 400000}],
            "2": [{"state": "NORMAL", "isPurchasable": True, "salePrice": 300000, "listPrice": 500000}],
            "3": [],
        }},
    })

    result = fetch_fastcampus_candidates(sources=[source], client=client)

    assert [c.source_id for c in result] == ["1", "2", "3"]
    assert result[0].badges == ("인기 급상승",)
    assert result[1].badges == ("BEST",)
    assert result[2].badges == ("NEW",)
    assert result[0].sale_price == 220000
    assert result[0].list_price == 400000
    assert result[0].source_url == f"{base}/popular"
    assert result[0].thumbnail_url.endswith("/1.webp")
    assert result[0].running_time_minutes == 750
    assert result[0].source_category_code == "DATASCIENCEDL"
    assert result[0].source_category_url == source.page_url
    assert all(c.title != "일반 강의" for c in result)


def test_fetch_combines_best_new_and_highlight_without_duplicates():
    base = "https://fastcampus.co.kr"
    source = FastCampusSource(f"{base}/category_online_aicreative", "AICREATIVE", "AI CREATIVE")
    client = Client({
        f"{base}/.api/categories/AICREATIVE": {"data": {"id": 921, "courses": [
            course(9, "all-tags", "복합 태그", "인기 급상승"),
        ]}},
        f"{base}/.api/courses/recommended/best": {"data": {"921": [9]}},
        f"{base}/.api/courses/marketing/latest": {"data": {"921": [9]}},
        (f"{base}/.api/courses/products", (("id", "9"),)): {"data": {"9": []}},
    })
    result = fetch_fastcampus_candidates(sources=[source], client=client)
    assert len(result) == 1
    assert result[0].badges == ("BEST", "NEW", "인기 급상승")


def test_fetch_fails_closed_when_a_category_request_fails():
    import pytest
    import httpx

    base = "https://fastcampus.co.kr"
    source = FastCampusSource(f"{base}/category_online_biz", "BIZ", "AI/업무생산성")
    client = Client({})
    client.get = lambda url, params=None: Response({}, status=503)
    with pytest.raises(httpx.HTTPStatusError):
        fetch_fastcampus_candidates(sources=[source], client=client)


def test_fetch_fails_closed_when_category_courses_are_unexpectedly_empty():
    import pytest

    base = "https://fastcampus.co.kr"
    source = FastCampusSource(f"{base}/category_online_biz", "BIZ", "AI/업무생산성")
    client = Client({
        f"{base}/.api/courses/recommended/best": {"data": {"1": []}},
        f"{base}/.api/courses/marketing/latest": {"data": {"1": []}},
        f"{base}/.api/categories/BIZ": {"data": {"id": 1, "courses": []}},
    })
    with pytest.raises(ValueError, match="과정 목록이 비어"):
        fetch_fastcampus_candidates(sources=[source], client=client)


def test_fetch_rejects_missing_badge_category_and_wrong_category_id():
    import pytest

    base = "https://fastcampus.co.kr"
    source = FastCampusSource(f"{base}/category_online_biz", "BIZ", "AI/업무생산성")
    payloads = {
        f"{base}/.api/courses/recommended/best": {"data": {}},
        f"{base}/.api/courses/marketing/latest": {"data": {"1": [1]}},
        f"{base}/.api/categories/BIZ": {"data": {"id": 999, "courses": [course(1, "x", "강의")]}},
    }
    with pytest.raises(ValueError, match="카테고리 ID"):
        fetch_fastcampus_candidates(sources=[source], client=Client(payloads))

    payloads[f"{base}/.api/categories/BIZ"]["data"]["id"] = 1
    with pytest.raises(ValueError, match="BEST 응답"):
        fetch_fastcampus_candidates(sources=[source], client=Client(payloads))


def test_fetch_normalizes_malformed_external_schema_to_value_error():
    import pytest

    base = "https://fastcampus.co.kr"
    source = FastCampusSource(f"{base}/category_online_biz", "BIZ", "AI/업무생산성")
    client = Client({
        f"{base}/.api/courses/recommended/best": {"data": {"1": [1]}},
        f"{base}/.api/courses/marketing/latest": {"data": {"1": []}},
        f"{base}/.api/categories/BIZ": {"data": []},
    })
    with pytest.raises(ValueError, match="카테고리 응답"):
        fetch_fastcampus_candidates(sources=[source], client=client)


def test_fetch_rejects_malformed_products_mapping():
    import pytest

    base = "https://fastcampus.co.kr"
    source = FastCampusSource(f"{base}/category_online_biz", "BIZ", "AI/업무생산성")
    client = Client({
        f"{base}/.api/courses/recommended/best": {"data": {"1": [1]}},
        f"{base}/.api/courses/marketing/latest": {"data": {"1": []}},
        f"{base}/.api/categories/BIZ": {"data": {"id": 1, "courses": [course(1, "x", "강의")]}},
        (f"{base}/.api/courses/products", (("id", "1"),)): {"data": []},
    })
    with pytest.raises(ValueError, match="상품 응답"):
        fetch_fastcampus_candidates(sources=[source], client=client)
