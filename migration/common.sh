#!/usr/bin/env bash
# NEXUS DB 이관 스크립트 공통 함수. 직접 실행하지 않는다.

MIGRATION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TABLE_FILE="$MIGRATION_DIR/nexus_tables.txt"

load_db_env() {
  local env_file="$1"
  local raw key value first last required
  if [[ ! -f "$env_file" ]]; then
    echo "환경 파일을 찾을 수 없습니다: $env_file" >&2
    return 1
  fi

  while IFS= read -r raw || [[ -n "$raw" ]]; do
    raw="${raw%$'\r'}"
    [[ -z "$raw" || "$raw" == \#* || "$raw" != *=* ]] && continue
    key="${raw%%=*}"
    value="${raw#*=}"
    case "$key" in
      DB_NAME|DB_USER|DB_PASSWORD|DB_HOST|DB_PORT)
        first="${value:0:1}"
        last="${value: -1}"
        if [[ ${#value} -ge 2 && (( "$first" == '"' && "$last" == '"' ) || ( "$first" == "'" && "$last" == "'" )) ]]; then
          value="${value:1:${#value}-2}"
        fi
        export "$key=$value"
        ;;
    esac
  done < "$env_file"

  for required in DB_NAME DB_USER DB_PASSWORD DB_HOST DB_PORT; do
    if [[ -z "${!required:-}" ]]; then
      echo "$env_file 에 $required 값이 없습니다." >&2
      return 1
    fi
  done
}

require_commands() {
  local command_name
  for command_name in "$@"; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
      echo "필수 명령을 찾을 수 없습니다: $command_name" >&2
      return 1
    fi
  done
}

run_psql() {
  PGPASSWORD="$DB_PASSWORD" psql -X -v ON_ERROR_STOP=1 \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" "$@"
}

run_pg_dump() {
  PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" "$@"
}

run_pg_restore() {
  PGPASSWORD="$DB_PASSWORD" pg_restore \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" "$@"
}

for_each_table() {
  local callback="$1" table
  while IFS= read -r table || [[ -n "$table" ]]; do
    [[ -z "$table" || "$table" == \#* ]] && continue
    "$callback" "$table"
  done < "$TABLE_FILE"
}

is_nexus_table() {
  case "$1" in
    categories|articles|members|auth_sessions|community_posts|community_post_likes|community_comments|meetup_events|meetup_collect_runs|courses|fastcampus_collect_runs|writer_sessions|writer_messages|brunch_collect_runs|newsletter_collect_runs) return 0 ;;
    *) return 1 ;;
  esac
}

is_nexus_sequence() {
  case "$1" in
    articles_id_seq|auth_sessions_id_seq|brunch_collect_runs_id_seq|categories_id_seq|community_comments_id_seq|community_posts_id_seq|courses_id_seq|fastcampus_collect_runs_id_seq|meetup_collect_runs_id_seq|meetup_events_id_seq|members_id_seq|newsletter_collect_runs_id_seq|writer_messages_id_seq|writer_sessions_telegram_user_id_seq) return 0 ;;
    *) return 1 ;;
  esac
}

is_nexus_index() {
  case "$1" in
    ix_articles_category_status_published|ix_articles_type_published|ix_auth_sessions_member|ix_community_comments_member|ix_community_comments_post|ix_community_posts_member|ix_community_posts_status_created|ix_courses_status_category_rank|ix_meetup_events_start|ix_writer_messages_user_created|ux_members_email) return 0 ;;
    *) return 1 ;;
  esac
}
