"""루트 migration 번들의 안전한 NEXUS 전용 DB 이관 계약."""
from pathlib import Path
import subprocess

from app.models import Base


ROOT = Path(__file__).resolve().parents[2]
MIGRATION_DIR = ROOT / "migration"
SHARED_TABLES = {"bc_merchant_validation", "naver_merchant_capture"}


def table_names() -> list[str]:
    lines = (MIGRATION_DIR / "nexus_tables.txt").read_text().splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def test_migration_table_manifest_matches_sqlalchemy_models():
    assert set(table_names()) == set(Base.metadata.tables)


def test_migration_table_manifest_excludes_shared_project_tables():
    assert set(table_names()).isdisjoint(SHARED_TABLES)


def test_migration_shell_scripts_have_valid_syntax():
    for name in ("common.sh", "export.sh", "import.sh", "verify.sh"):
        script = MIGRATION_DIR / name
        assert script.is_file()
        subprocess.run(["bash", "-n", str(script)], check=True)


def test_generated_dump_artifacts_are_gitignored():
    gitignore = (ROOT / ".gitignore").read_text()
    assert "migration/artifacts/" in gitignore


def test_export_protects_sensitive_artifacts():
    script = (MIGRATION_DIR / "export.sh").read_text()
    assert "umask 077" in script
    assert "SHA256SUMS" in script


def test_import_replaces_only_nexus_tables_in_restore_transaction():
    script = (MIGRATION_DIR / "import.sh").read_text()
    assert "--clean" not in script
    assert " CASCADE;" not in script
    assert "SHA256SUMS" in script
    assert "--use-list" in script
    assert "--single-transaction" in script
    assert "DROP TABLE IF EXISTS" in script
    for table in table_names():
        assert f"public.{table}" in script
    assert 'TABLE public $table' in script
    assert 'TABLE DATA public $table' in script
    assert "schema columns mismatch" in script
    assert "허용되지 않은 TOC 객체" in script
    assert script.index("DROP TABLE IF EXISTS") < script.index('cat "$RESTORE_BODY"')


def test_verify_validates_manifest_table_before_building_sql():
    script = (MIGRATION_DIR / "verify.sh").read_text()
    validation = script.index('is_nexus_table "$table"')
    query = script.index('SELECT count(*) FROM public.')
    assert validation < query
