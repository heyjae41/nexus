"""브런치 원글 이동 URL 규칙 테스트: 항상 ?ref=nexus.bccard.ai 를 부착한다."""
import pytest

from app.services.links import with_ref


def test_appends_ref_to_plain_url():
    assert (
        with_ref("https://brunch.co.kr/@writer/123")
        == "https://brunch.co.kr/@writer/123?ref=nexus.bccard.ai"
    )


def test_appends_with_ampersand_when_query_exists():
    assert (
        with_ref("https://brunch.co.kr/@writer/123?foo=1")
        == "https://brunch.co.kr/@writer/123?foo=1&ref=nexus.bccard.ai"
    )


def test_does_not_duplicate_ref():
    url = "https://brunch.co.kr/@writer/123?ref=nexus.bccard.ai"
    assert with_ref(url) == url


def test_preserves_fragment():
    assert (
        with_ref("https://brunch.co.kr/@writer/123#comments")
        == "https://brunch.co.kr/@writer/123?ref=nexus.bccard.ai#comments"
    )


# --- 보안 LOW: 수집 소스가 넘긴 javascript:/data: 주소는 ref 를 붙여 돌려주지 않는다 ---

@pytest.mark.parametrize(
    "url", ["javascript:alert(1)//", "data:text/html,x", "//evil.com/x", "mailto:a@b", "", None]
)
def test_non_http_urls_become_none(url):
    assert with_ref(url) is None


def test_serializers_drop_unsafe_external_links():
    from datetime import datetime, timezone

    from app.models import Article
    from app.serializers import article_link

    article = Article(
        id=1, category_id=1, article_type="column", title="t", source_type="brunch",
        source_url="javascript:alert(1)", published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert article_link(article) == (None, True)
