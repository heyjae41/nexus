#!/usr/bin/env bash
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

TARGET_ENV="${1:-}"
DUMP_FILE="${2:-$SCRIPT_DIR/artifacts/nexus.dump}"
ARTIFACT_DIR="$(dirname "$DUMP_FILE")"
CHECKSUM_FILE="$ARTIFACT_DIR/SHA256SUMS"
RESTORE_LIST="$ARTIFACT_DIR/restore.list"
COUNTS_FILE="$ARTIFACT_DIR/row_counts.tsv"
COLUMNS_FILE="$ARTIFACT_DIR/schema_columns.tsv"

if [[ -z "$TARGET_ENV" ]]; then
  echo "사용법: $0 <target-env> [nexus.dump]" >&2
  exit 2
fi
for required_file in "$DUMP_FILE" "$CHECKSUM_FILE" "$RESTORE_LIST" "$COUNTS_FILE" "$COLUMNS_FILE"; do
  if [[ ! -f "$required_file" || -L "$required_file" ]]; then
    echo "필수 이관 파일이 없거나 심볼릭 링크입니다: $required_file" >&2
    exit 1
  fi
done

require_commands psql pg_restore diff
if command -v shasum >/dev/null 2>&1; then
  (cd "$ARTIFACT_DIR" && shasum -a 256 -c SHA256SUMS)
elif command -v sha256sum >/dev/null 2>&1; then
  (cd "$ARTIFACT_DIR" && sha256sum -c SHA256SUMS)
else
  echo "SHA-256 검사 도구가 없습니다." >&2
  exit 1
fi
load_db_env "$TARGET_ENV"
run_psql -Atc 'SELECT 1' >/dev/null

TOC_FILE="$(mktemp)"
RESTORE_BODY="$(mktemp)"
RESTORE_SQL="$(mktemp)"
trap 'rm -f "$TOC_FILE" "$RESTORE_BODY" "$RESTORE_SQL"' EXIT
pg_restore --list "$DUMP_FILE" > "$TOC_FILE"
if ! diff -u "$RESTORE_LIST" "$TOC_FILE"; then
  echo "덤프 TOC와 검증된 restore.list가 다릅니다." >&2
  exit 1
fi
if grep -Eq 'bc_merchant_validation|naver_merchant_capture' "$TOC_FILE"; then
  echo "안전 검사 실패: 공유 테이블이 덤프에 포함되었습니다." >&2
  exit 1
fi

# pg_restore가 실행할 수 있는 객체를 NEXUS 테이블과 종속 객체로만 제한한다.
TABLE_RE='^[0-9]+; [0-9]+ [0-9]+ TABLE public ([a-z_]+) [^ ]+$'
TABLE_DATA_RE='^[0-9]+; [0-9]+ [0-9]+ TABLE DATA public ([a-z_]+) [^ ]+$'
DEFAULT_RE='^[0-9]+; [0-9]+ [0-9]+ DEFAULT public ([a-z_]+) [a-z_]+ [^ ]+$'
CONSTRAINT_RE='^[0-9]+; [0-9]+ [0-9]+ (FK )?CONSTRAINT public ([a-z_]+) [a-z_]+ [^ ]+$'
SEQUENCE_RE='^[0-9]+; [0-9]+ [0-9]+ SEQUENCE public ([a-z_]+) [^ ]+$'
SEQUENCE_META_RE='^[0-9]+; [0-9]+ [0-9]+ SEQUENCE (OWNED BY|SET) public ([a-z_]+) [^ ]+$'
INDEX_RE='^[0-9]+; [0-9]+ [0-9]+ INDEX public ([a-z_]+) [^ ]+$'
while IFS= read -r toc_line || [[ -n "$toc_line" ]]; do
  [[ -z "$toc_line" || "$toc_line" == \;* ]] && continue
  if [[ "$toc_line" =~ $TABLE_RE || "$toc_line" =~ $TABLE_DATA_RE || "$toc_line" =~ $DEFAULT_RE ]]; then
    is_nexus_table "${BASH_REMATCH[1]}" || { echo "허용되지 않은 TOC 테이블: $toc_line" >&2; exit 1; }
  elif [[ "$toc_line" =~ $CONSTRAINT_RE ]]; then
    is_nexus_table "${BASH_REMATCH[2]}" || { echo "허용되지 않은 TOC 제약조건: $toc_line" >&2; exit 1; }
  elif [[ "$toc_line" =~ $SEQUENCE_RE ]]; then
    is_nexus_sequence "${BASH_REMATCH[1]}" || { echo "허용되지 않은 TOC 시퀀스: $toc_line" >&2; exit 1; }
  elif [[ "$toc_line" =~ $SEQUENCE_META_RE ]]; then
    is_nexus_sequence "${BASH_REMATCH[2]}" || { echo "허용되지 않은 TOC 시퀀스 메타데이터: $toc_line" >&2; exit 1; }
  elif [[ "$toc_line" =~ $INDEX_RE ]]; then
    is_nexus_index "${BASH_REMATCH[1]}" || { echo "허용되지 않은 TOC 인덱스: $toc_line" >&2; exit 1; }
  else
    echo "허용되지 않은 TOC 객체: $toc_line" >&2
    exit 1
  fi
done < "$TOC_FILE"

check_dump_table() {
  local table="$1"
  if ! grep -Eq "TABLE public $table( |$)" "$TOC_FILE"; then
    echo "덤프에 TABLE 정의가 없습니다: $table" >&2
    exit 1
  fi
  if ! grep -Eq "TABLE DATA public $table( |$)" "$TOC_FILE"; then
    echo "덤프에 TABLE DATA가 없습니다: $table" >&2
    exit 1
  fi
}
for_each_table check_dump_table

pg_restore --exit-on-error --no-owner --no-privileges \
  --use-list="$RESTORE_LIST" --file="$RESTORE_BODY" "$DUMP_FILE"

# NEXUS 객체 교체와 복원을 같은 트랜잭션에서 수행한다.
# CASCADE를 사용하지 않아 타 프로젝트 객체가 NEXUS를 참조하면 안전하게 실패한다.
cat > "$RESTORE_SQL" <<'SQL'
SET lock_timeout = '10s';
DROP TABLE IF EXISTS
  public.brunch_collect_runs,
  public.community_comments,
  public.community_post_likes,
  public.community_posts,
  public.writer_messages,
  public.writer_sessions,
  public.meetup_collect_runs,
  public.meetup_events,
  public.articles,
  public.members,
  public.categories;
SQL
cat "$RESTORE_BODY" >> "$RESTORE_SQL"

# 같은 트랜잭션에서 복원 데이터 건수를 검사해 실패 시 전체 복원을 롤백한다.
MANIFEST_ROWS=0
SEEN_TABLES=" "
while IFS=$'\t' read -r table expected; do
  [[ "$table" == "table_name" ]] && continue
  is_nexus_table "$table" || { echo "허용되지 않은 테이블이 건수 매니페스트에 있습니다: $table" >&2; exit 1; }
  if [[ "$SEEN_TABLES" == *" $table "* ]]; then
    echo "중복 테이블이 건수 매니페스트에 있습니다: $table" >&2
    exit 1
  fi
  SEEN_TABLES+="$table "
  MANIFEST_ROWS=$((MANIFEST_ROWS + 1))
  [[ "$expected" =~ ^[0-9]+$ ]] || { echo "잘못된 행 수: $table=$expected" >&2; exit 1; }
  printf '\nDO $$ BEGIN IF (SELECT count(*) FROM public."%s") <> %s THEN RAISE EXCEPTION '\''row count mismatch: %s'\''; END IF; END $$;\n' \
    "$table" "$expected" "$table" >> "$RESTORE_SQL"
done < "$COUNTS_FILE"
if [[ "$MANIFEST_ROWS" -ne 11 ]]; then
  echo "건수 매니페스트의 NEXUS 테이블 수가 11개가 아닙니다: $MANIFEST_ROWS" >&2
  exit 1
fi

# 컬럼 정의도 복원 트랜잭션 안에서 비교한다.
COLUMNS_PATH="$(cd "$ARTIFACT_DIR" && pwd)/schema_columns.tsv"
COLUMNS_PATH="${COLUMNS_PATH//\'/\'\'}"
cat >> "$RESTORE_SQL" <<SQL
SET search_path = public, pg_catalog;
CREATE TEMP TABLE nexus_expected_columns (
  table_name text, ordinal_position integer, column_name text,
  data_type text, is_nullable text, column_default text
);
\\copy nexus_expected_columns FROM '$COLUMNS_PATH' WITH (FORMAT csv, DELIMITER E'\\t', HEADER true, NULL '\\N')
DO \$\$
BEGIN
  IF EXISTS (
    (SELECT * FROM nexus_expected_columns
     EXCEPT
     SELECT table_name, ordinal_position, column_name, data_type, is_nullable, coalesce(column_default, '')
     FROM information_schema.columns
     WHERE table_schema = 'public' AND table_name IN (
       'categories','articles','members','community_posts','community_post_likes','community_comments',
       'meetup_events','meetup_collect_runs','writer_sessions','writer_messages','brunch_collect_runs'
     ))
    UNION ALL
    (SELECT table_name, ordinal_position, column_name, data_type, is_nullable, coalesce(column_default, '')
     FROM information_schema.columns
     WHERE table_schema = 'public' AND table_name IN (
       'categories','articles','members','community_posts','community_post_likes','community_comments',
       'meetup_events','meetup_collect_runs','writer_sessions','writer_messages','brunch_collect_runs'
     )
     EXCEPT SELECT * FROM nexus_expected_columns)
  ) THEN
    RAISE EXCEPTION 'schema columns mismatch';
  END IF;
END \$\$;
SQL

run_psql --single-transaction --file="$RESTORE_SQL"

bash "$SCRIPT_DIR/verify.sh" "$TARGET_ENV" "$ARTIFACT_DIR"

echo "NEXUS 스키마와 데이터 이관 완료"
