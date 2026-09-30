"""기동 시 Secrets Manager 키 이름만 로그로 남긴다. 값은 출력하지 않는다."""
import json

import boto3

SECRET_IDS = (
    "nexus-app-credentials",
    "nexus-mongodb-credentials",
    "nexus-db-credentials",
)
REGION = "ap-northeast-2"


def describe_secret_keys(secret_id: str, secret_string: str) -> str:
    keys = _key_names(secret_string)
    present = "yes" if "SUPER_ADMIN" in keys else "no"
    return f"[secrets] {secret_id} keys={','.join(keys)} SUPER_ADMIN={present}"


def log_configured_secrets(client, secret_ids=SECRET_IDS, printer=print) -> None:
    for secret_id in secret_ids:
        printer(_line_for(client, secret_id))


def log_secret_keys_from_aws(printer=print) -> None:
    client = boto3.client("secretsmanager", region_name=REGION)
    log_configured_secrets(client, printer=printer)


def _key_names(secret_string: str) -> list[str]:
    data = json.loads(secret_string)
    if not isinstance(data, dict):
        raise ValueError("secret is not a json object")
    return sorted(str(key) for key in data)


def _line_for(client, secret_id: str) -> str:
    try:
        response = client.get_secret_value(SecretId=secret_id)
    except Exception as exc:
        return f"[secrets] {secret_id} error={_error_name(exc)}"
    raw = response.get("SecretString")
    if not raw:
        return f"[secrets] {secret_id} error=empty"
    try:
        return describe_secret_keys(secret_id, raw)
    except (json.JSONDecodeError, ValueError):
        return f"[secrets] {secret_id} error=not-json"


def _error_name(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        code = response.get("Error", {}).get("Code")
        if code:
            return str(code)
    return type(exc).__name__
