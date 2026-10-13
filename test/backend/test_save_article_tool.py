"""발행 도구(save_article.py)의 화이트리스트 검사 — 불변식 4: 도구 자체가 거른다."""
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / ".claude/skills/nexus-writer/tools"
sys.path.insert(0, str(TOOLS))

import save_article  # noqa: E402

PAYLOAD = {
    "title": "제목", "article_type": "guide", "summary": "요약", "author": "작가",
    "body_html": "<p>본문</p>", "key_visual_html": "<svg/>",
}


@pytest.fixture()
def tool_env(tmp_path, monkeypatch):
    whitelist = tmp_path / ".writer_whitelist"
    whitelist.write_text("111\n", encoding="utf-8")
    contents = tmp_path / "contents"
    article = tmp_path / "article.json"
    article.write_text(json.dumps(PAYLOAD), encoding="utf-8")
    monkeypatch.setattr(save_article, "ingest_now", lambda *_a, **_k: None)
    return whitelist, contents, article


def test_denied_user_cannot_publish(tool_env, capsys):
    whitelist, contents, article = tool_env
    code = save_article.main([str(article)], telegram_user_id="999", whitelist_path=str(whitelist), contents_dir=contents)
    assert code == 1
    assert "DENIED" in capsys.readouterr().out
    assert not contents.exists() or not any(contents.iterdir())


def test_missing_user_id_is_denied(tool_env, capsys):
    whitelist, contents, article = tool_env
    code = save_article.main([str(article)], telegram_user_id=None, whitelist_path=str(whitelist), contents_dir=contents)
    assert code == 1 and "DENIED" in capsys.readouterr().out


def test_allowed_user_publishes(tool_env):
    whitelist, contents, article = tool_env
    code = save_article.main([str(article)], telegram_user_id="111", whitelist_path=str(whitelist), contents_dir=contents)
    assert code == 0
    assert len(list(contents.glob("*_가이드_제목.html"))) == 1


def test_user_id_comes_from_env_or_argv(tool_env, monkeypatch):
    whitelist, contents, article = tool_env
    monkeypatch.setenv("NEXUS_TELEGRAM_USER_ID", "111")
    assert save_article.main([str(article)], whitelist_path=str(whitelist), contents_dir=contents) == 0
    monkeypatch.delenv("NEXUS_TELEGRAM_USER_ID")
    assert save_article.main([str(article), "--user", "999"], whitelist_path=str(whitelist), contents_dir=contents) == 1


# --- 2차 리뷰: 호스트(hermes)가 넣는 환경변수가 argv 보다 우선하며, 둘이 다르면 거부 ---

def test_argv_user_is_accepted_when_host_env_absent(tool_env, monkeypatch):
    whitelist, contents, article = tool_env
    monkeypatch.delenv("NEXUS_TELEGRAM_USER_ID", raising=False)
    assert save_article.main([str(article), "--user", "111"], whitelist_path=str(whitelist), contents_dir=contents) == 0


@pytest.mark.parametrize("host_env", ["", "222"], ids=["empty-env", "env-differs-from-argv"])
def test_host_env_overrides_valid_argv_and_denies(tool_env, monkeypatch, capsys, host_env):
    """호스트 환경변수가 있으면 그것만 믿는다: 비어 있거나 --user 와 다르면 거부."""
    whitelist, contents, article = tool_env
    whitelist.write_text("111\n222\n", encoding="utf-8")
    monkeypatch.setenv("NEXUS_TELEGRAM_USER_ID", host_env)
    assert save_article.main([str(article), "--user", "111"], whitelist_path=str(whitelist), contents_dir=contents) == 1
    assert "DENIED" in capsys.readouterr().out
