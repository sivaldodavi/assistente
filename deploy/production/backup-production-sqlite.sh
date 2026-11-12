#!/usr/bin/env bash
set -euo pipefail

container=assistente-academico-production
backup_dir=/opt/servidor/backups/assistente-academico-production/daily
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
container_backup="/tmp/assistente-academico-production-${timestamp}.sqlite3"

install -d -o root -g root -m 700 "$backup_dir"
temporary="$(mktemp "$backup_dir/.production.XXXXXX")"

cleanup() {
  rm -f -- "$temporary"
  docker exec -u 0 "$container" rm -f "$container_backup" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker exec "$container" sqlite3 /rails/storage/production.sqlite3 ".backup '$container_backup'"
docker cp "$container:$container_backup" "$temporary"
integrity="$(docker exec -u 0 "$container" sqlite3 "$container_backup" 'PRAGMA integrity_check;')"
if [[ "$integrity" != "ok" ]]; then
  printf 'Backup integrity check failed: %s\n' "$integrity" >&2
  exit 1
fi

chmod 600 "$temporary"
mv -- "$temporary" "$backup_dir/production-${timestamp}.sqlite3"

mapfile -t obsolete < <(
  find "$backup_dir" -maxdepth 1 -type f -name 'production-*.sqlite3' -printf '%f\n' |
    sort -r |
    tail -n +8
)
for backup in "${obsolete[@]}"; do
  rm -f -- "$backup_dir/$backup"
done
