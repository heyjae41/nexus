"""작가 화이트리스트 테스트.

문서 루트의 .writer_whitelist 파일(숫자 텔레그램 userid, 한 줄당 하나)에
등록된 사용자만 글을 쓸 수 있다.
"""
from app.services.writer_whitelist import is_allowed_writer, load_whitelist


def write_wl(tmp_path, content):
    p = tmp_path / ".writer_whitelist"
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_load_whitelist_parses_ids(tmp_path):
    path = write_wl(tmp_path, "8174778078\n12345\n")
    assert load_whitelist(path) == {8174778078, 12345}


def test_load_whitelist_ignores_comments_blanks_and_junk(tmp_path):
    path = write_wl(tmp_path, "# 운영 작가\n8174778078\n\nabc\n  99  \n")
    assert load_whitelist(path) == {8174778078, 99}


def test_load_whitelist_missing_file_returns_empty(tmp_path):
    assert load_whitelist(str(tmp_path / "없는파일")) == set()


def test_is_allowed_writer(tmp_path):
    path = write_wl(tmp_path, "8174778078\n")
    assert is_allowed_writer(8174778078, path) is True
    assert is_allowed_writer("8174778078", path) is True  # 문자열 입력 허용
    assert is_allowed_writer(999, path) is False


def test_is_allowed_writer_invalid_id(tmp_path):
    path = write_wl(tmp_path, "8174778078\n")
    assert is_allowed_writer("abc", path) is False
    assert is_allowed_writer(None, path) is False


def test_empty_whitelist_denies_everyone(tmp_path):
    path = write_wl(tmp_path, "# 아무도 없음\n")
    assert is_allowed_writer(8174778078, path) is False


def test_unicode_digit_entries_are_ignored(tmp_path):
    """isdigit() 는 통과하지만 int() 가 실패하는 유니코드 숫자는 무시한다 (fail-closed)."""
    path = write_wl(tmp_path, "²³\n8174778078\n")
    assert load_whitelist(path) == {8174778078}
