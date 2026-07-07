"""브런치 원글 이동 URL 규칙 테스트: 항상 ?ref=nexus.bccard.ai 를 부착한다."""
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
