#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

TARGET_ENV="${1:-}"
ARTIFACT_DIR="${2:-$SCRIPT_DIR/artifacts}"
COUNTS_FILE="$ARTIFACT_DIR/row_counts.tsv"
COLUMNS_FILE="$ARTIFACT_DIR/schema_columns.tsv"

if [[ -z "$TARGET_ENV" ]]; then
  echo "사용법: $0 <target-env> [artifact-dir]" >&2
  exit 2
fi
if [[ ! -f "$COUNTS_FILE" || ! -f "$COLUMNS_FILE" ]]; then
  echo "검증 파일이 없습니다. 먼저 export.sh를 실행하세요." >&2
  exit 1
fi

require_commands psql diff
load_db_env "$TARGET_ENV"
run_psql -Atc 'SELECT 1' >/dev/null

FAILED=0
while IFS=$'\t' read -r table expected; do
  [[ "$table" == "table_name" ]] && continue
  if ! is_nexus_table "$table" || [[ ! "$expected" =~ ^[0-9]+$ ]]; then
    echo "잘못된 건수 매니페스트 행입니다: $table=$expected" >&2
    exit 1
  fi
  actual="$(run_psql -Atc "SELECT count(*) FROM public.\"$table\"")"
  if [[ "$actual" != "$expected" ]]; then
    echo "건수 불일치: $table (기대 $expected, 실제 $actual)" >&2
    FAILED=1
  else
    echo "건수 일치: $table = $actual"
  fi
done < "$COUNTS_FILE"

ACTUAL_COLUMNS="$(mktemp)"
trap 'rm -f "$ACTUAL_COLUMNS"' EXIT
printf 'table_name\tordinal_position\tcolumn_name\tdata_type\tis_nullable\tcolumn_default\n' > "$ACTUAL_COLUMNS"
write_actual_columns() {
  local table="$1"
  run_psql -At -F $'\t' -c "SELECT table_name, ordinal_position, column_name, data_type, is_nullable, coalesce(column_default, '') FROM information_schema.columns WHERE table_schema='public' AND table_name='$table' ORDER BY ordinal_position" >> "$ACTUAL_COLUMNS"
}
for_each_table write_actual_columns

if ! diff -u "$COLUMNS_FILE" "$ACTUAL_COLUMNS"; then
  echo "스키마 컬럼 정의가 소스와 다릅니다." >&2
  FAILED=1
else
  echo "스키마 컬럼 정의 일치"
fi

if [[ "$FAILED" -ne 0 ]]; then
  exit 1
fi
echo "이관 검증 완료"
