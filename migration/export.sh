#!/usr/bin/env bash
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

SOURCE_ENV="${1:-$SCRIPT_DIR/../.env}"
OUTPUT_DIR="${2:-$SCRIPT_DIR/artifacts}"
OUTPUT_PARENT="$(dirname "$OUTPUT_DIR")"

if [[ -e "$OUTPUT_DIR" || -L "$OUTPUT_DIR" ]]; then
  echo "출력 경로가 이미 존재합니다: $OUTPUT_DIR" >&2
  echo "기존 덤프와 새 매니페스트가 섞이지 않도록 다른 경로를 지정하세요." >&2
  exit 1
fi

require_commands psql pg_dump pg_restore
load_db_env "$SOURCE_ENV"
mkdir -p "$OUTPUT_PARENT"
if ! mkdir "$OUTPUT_DIR"; then
  echo "출력 경로를 배타적으로 예약하지 못했습니다: $OUTPUT_DIR" >&2
  exit 1
fi
WORK_DIR="$OUTPUT_DIR/.building"
mkdir "$WORK_DIR"
trap 'rm -rf "$WORK_DIR"' EXIT
DUMP_FILE="$WORK_DIR/nexus.dump"
SCHEMA_FILE="$WORK_DIR/schema.sql"
COUNTS_FILE="$WORK_DIR/row_counts.tsv"
COLUMNS_FILE="$WORK_DIR/schema_columns.tsv"

TABLE_ARGS=()
append_table_arg() {
  TABLE_ARGS+=("--table=public.$1")
}
for_each_table append_table_arg

# 연결 및 테이블 존재 여부를 먼저 확인해 부분 덤프 생성을 막는다.
check_table() {
  local table="$1" exists
  exists="$(run_psql -Atc "SELECT to_regclass('public.$table') IS NOT NULL")"
  if [[ "$exists" != "t" ]]; then
    echo "소스 DB에 필수 테이블이 없습니다: $table" >&2
    exit 1
  fi
}
for_each_table check_table

run_pg_dump --format=custom --no-owner --no-privileges \
  "${TABLE_ARGS[@]}" --file="$DUMP_FILE"
run_pg_dump --schema-only --format=plain --no-owner --no-privileges \
  "${TABLE_ARGS[@]}" --file="$SCHEMA_FILE"

printf 'table_name\trow_count\n' > "$COUNTS_FILE"
write_count() {
  local table="$1" count
  count="$(run_psql -Atc "SELECT count(*) FROM public.\"$table\"")"
  printf '%s\t%s\n' "$table" "$count" >> "$COUNTS_FILE"
}
for_each_table write_count

printf 'table_name\tordinal_position\tcolumn_name\tdata_type\tis_nullable\tcolumn_default\n' > "$COLUMNS_FILE"
write_columns() {
  local table="$1"
  run_psql -At -F $'\t' -c "SELECT table_name, ordinal_position, column_name, data_type, is_nullable, coalesce(column_default, '') FROM information_schema.columns WHERE table_schema='public' AND table_name='$table' ORDER BY ordinal_position" >> "$COLUMNS_FILE"
}
for_each_table write_columns

# 덤프가 읽을 수 있고 공유 테이블을 포함하지 않는지 즉시 검증한다.
pg_restore --list "$DUMP_FILE" >/dev/null
if pg_restore --list "$DUMP_FILE" | grep -Eq 'bc_merchant_validation|naver_merchant_capture'; then
  echo "안전 검사 실패: 공유 테이블이 덤프에 포함되었습니다." >&2
  exit 1
fi
pg_restore --list "$DUMP_FILE" > "$WORK_DIR/restore.list"

if command -v shasum >/dev/null 2>&1; then
  (cd "$WORK_DIR" && shasum -a 256 nexus.dump restore.list row_counts.tsv schema_columns.tsv schema.sql > SHA256SUMS)
elif command -v sha256sum >/dev/null 2>&1; then
  (cd "$WORK_DIR" && sha256sum nexus.dump restore.list row_counts.tsv schema_columns.tsv schema.sql > SHA256SUMS)
else
  echo "SHA-256 검사 도구가 없습니다." >&2
  exit 1
fi

for artifact in nexus.dump restore.list row_counts.tsv schema_columns.tsv schema.sql; do
  mv "$WORK_DIR/$artifact" "$OUTPUT_DIR/$artifact"
done
mv "$WORK_DIR/SHA256SUMS" "$OUTPUT_DIR/SHA256SUMS"
rmdir "$WORK_DIR"
trap - EXIT
cp "$OUTPUT_DIR/schema.sql" "$SCRIPT_DIR/schema.sql.tmp"
mv "$SCRIPT_DIR/schema.sql.tmp" "$SCRIPT_DIR/schema.sql"

printf '이관 덤프 생성 완료: %s/nexus.dump\n' "$OUTPUT_DIR"
printf '스키마 문서 생성 완료: %s\n' "$SCRIPT_DIR/schema.sql"
printf '데이터 건수 기록 완료: %s/row_counts.tsv\n' "$OUTPUT_DIR"
