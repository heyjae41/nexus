"""Secrets Manager 조회 로그는 키 이름만 남긴다."""
import json

from app.services.secret_keys import describe_secret_keys, log_configured_secrets


def test_describe_secret_keys_lists_names_without_values():
    raw = json.dumps({"DB_PASSWORD": "s3cret-value", "SUPER_ADMIN": "heyjae"})
    line = describe_secret_keys("nexus-app-credentials", raw)
    assert "DB_PASSWORD" in line
    assert "SUPER_ADMIN=yes" in line
    assert "s3cret-value" not in line
    assert "heyjae" not in line


def test_describe_secret_keys_marks_missing_super_admin():
    line = describe_secret_keys("nexus-db-credentials", json.dumps({"DB_USER": "nexus"}))
    assert line == "[secrets] nexus-db-credentials keys=DB_USER SUPER_ADMIN=no"


def test_log_configured_secrets_reports_lookup_error_without_payload():
    class Broken:
        def get_secret_value(self, SecretId):
            raise RuntimeError("hidden-secret-body")

    lines = []
    log_configured_secrets(Broken(), ("nexus-app-credentials",), printer=lines.append)
    assert lines == ["[secrets] nexus-app-credentials error=RuntimeError"]
    assert "hidden-secret-body" not in lines[0]
