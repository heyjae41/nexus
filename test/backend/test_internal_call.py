"""파드 안 내부 API 호출 헬퍼(app.internal_call) — 이미지에 curl 이 없어 운영 호출은 이 모듈로 한다."""
import io
import urllib.error
from contextlib import contextmanager

import pytest

from app.internal_call import build_request, call, main


@pytest.mark.parametrize(
    "path",
    ["content/resanitize", "/content/resanitize", "api/internal/content/resanitize",
     "/api/internal/content/resanitize", " content/resanitize "],
)
def test_build_request_normalizes_paths_to_loopback_internal_url(path):
    request = build_request(path)
    assert request.full_url == "http://127.0.0.1:8000/api/internal/content/resanitize"
    assert request.get_method() == "POST"


def test_build_request_rejects_empty_path():
    with pytest.raises(ValueError):
        build_request("/api/internal/")


class _Response(io.BytesIO):
    status = 200


def _opener_returning(body: bytes):
    @contextmanager
    def opener(request, timeout):
        yield _Response(body)

    return opener


def test_call_returns_status_and_body():
    status, body = call("media/backfill", opener=_opener_returning(b'{"success":true}'))
    assert (status, body) == (200, '{"success":true}')


def test_call_returns_error_body_on_http_error():
    def opener(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 403, "forbidden", {}, io.BytesIO(b'{"error":"x"}'))

    assert call("media/backfill", opener=opener) == (403, '{"error":"x"}')


def test_main_prints_json_and_maps_status_to_exit_code(capsys):
    assert main(["content/resanitize"], opener=_opener_returning(b'{"data":{"changed":1}}')) == 0
    assert capsys.readouterr().out.strip() == '{"data": {"changed": 1}}'

    def denied(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 403, "forbidden", {}, io.BytesIO(b"nope"))

    assert main(["content/resanitize"], opener=denied) == 1
    assert main([], opener=denied) == 2
