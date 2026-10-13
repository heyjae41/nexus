"""작가 도구 공통의 사용자 id 출처 규칙.

텔레그램 userid 는 호스트(hermes)가 도구 환경에 넣는 NEXUS_TELEGRAM_USER_ID 가 정답이다.
모델이 고르는 argv 의 id 는 메시지 본문의 "telegram_user_id: ..." 흉내 등 프롬프트
인젝션으로 바뀔 수 있으므로, 환경변수가 있으면 argv 는 같을 때만 허용한다.
환경변수가 비어 있으면 거부하고, 아예 없을 때만 argv 를 쓴다(호스트 연동 전 호환, 더 약한 보호).
"""
import os
from collections.abc import Mapping

HOST_USER_ENV = "NEXUS_TELEGRAM_USER_ID"


def resolve_writer_id(arg_user: str | None, env: Mapping[str, str] | None = None) -> str | None:
    """(argv 의 id, 환경) → 신뢰할 사용자 id. None 이면 거부."""
    source = os.environ if env is None else env
    host_user = source.get(HOST_USER_ENV)
    if host_user is None:
        return arg_user
    host_user = host_user.strip()
    if not host_user:
        return None
    if arg_user is not None and arg_user.strip() != host_user:
        return None
    return host_user
