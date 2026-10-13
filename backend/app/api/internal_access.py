"""`/api/internal/*` 앱 레벨 접근 통제.

nginx 의 `return 403` 은 프록시를 거친 요청만 막는다. 클러스터 안의 다른 파드나 백엔드로
직접 라우팅되는 인그레스는 그 벽을 지나므로 앱도 스스로 거른다:
- `X-Internal-Token` 이 설정값(INTERNAL_API_TOKEN)과 일치하면 허용 (빈 설정은 절대 일치하지 않음)
- 아니면 정확히 127.0.0.1 / ::1 에서 온 요청만 허용 (파드 안 `python -m app.internal_call`).
  127.0.0.0/8 전체를 받으면 서비스 메시 사이드카(예: Istio 127.0.0.6)가 중계한 모든 요청이 통과한다.
"""
import secrets

from fastapi import Header, HTTPException, Request

from app.config import get_settings

TOKEN_HEADER = "X-Internal-Token"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1"})


def _is_loopback(client) -> bool:
    return client is not None and client.host in LOOPBACK_HOSTS


def _token_matches(provided: str | None) -> bool:
    expected = get_settings().internal_api_token
    if not expected or not provided:
        return False
    return secrets.compare_digest(provided.encode(), expected.encode())


def require_internal_access(
    request: Request, x_internal_token: str | None = Header(default=None)
) -> None:
    if _token_matches(x_internal_token) or _is_loopback(request.client):
        return
    raise HTTPException(
        status_code=403,
        detail="내부 API 는 파드 안(루프백) 또는 X-Internal-Token 으로만 호출할 수 있습니다",
    )
