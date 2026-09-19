#!/bin/bash
#
# Nightly backup for CMN Artist Portal.
#
# Backs up, into a single restic repository on Backblaze B2:
#   1. A pg_dump of the Postgres database (via `docker compose exec`)
#   2. The media volume (uploaded music + album art)
#   3. The Navidrome sqlite database (excluding its regenerable cache)
#
# Config lives in backup.env next to this script (copy from backup.env.example).
# Intended to run via the cmn-backup.timer systemd unit (see cmn-backup.service).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${BACKUP_ENV_FILE:-$SCRIPT_DIR/backup.env}"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Missing config: $ENV_FILE (copy backup.env.example and fill it in)" >&2
    exit 1
fi
# shellcheck disable=SC1090
source "$ENV_FILE"

: "${RESTIC_REPOSITORY:?must be set in backup.env}"
: "${RESTIC_PASSWORD:?must be set in backup.env}"
: "${B2_ACCOUNT_ID:?must be set in backup.env}"
: "${B2_ACCOUNT_KEY:?must be set in backup.env}"
: "${PROJECT_DIR:?must be set in backup.env}"
: "${MEDIA_DIR:?must be set in backup.env}"
: "${NAVIDROME_DATA_DIR:?must be set in backup.env}"
: "${DBUSER:?must be set in backup.env}"
: "${DBNAME:?must be set in backup.env}"
: "${DBPASS:?must be set in backup.env}"

export RESTIC_REPOSITORY RESTIC_PASSWORD B2_ACCOUNT_ID B2_ACCOUNT_KEY

KEEP_DAILY="${KEEP_DAILY:-7}"
KEEP_WEEKLY="${KEEP_WEEKLY:-4}"
KEEP_MONTHLY="${KEEP_MONTHLY:-6}"

WORK_DIR="$(mktemp -d)"
LOG_FILE="$WORK_DIR/backup.log"
exec > >(tee -a "$LOG_FILE") 2>&1

log() { echo "[$(date -Iseconds)] $*"; }

# Reuses the app's own Gmail SMTP creds (see cmn_artist/settings.py) so we
# don't need a separate mail setup just for this script. Notification is
# best-effort — a failed email must never mask (or fail) the backup itself.
notify() {
    local subject="$1"
    [[ -z "${NOTIFY_EMAIL:-}" || -z "${EMAIL_HOST_USER:-}" || -z "${EMAIL_HOST_PASSWORD:-}" ]] && return 0

    local msg_file="$WORK_DIR/notify.eml"
    {
        printf 'From: %s\r\n' "${DEFAULT_FROM_EMAIL:-$EMAIL_HOST_USER}"
        printf 'To: %s\r\n' "$NOTIFY_EMAIL"
        printf 'Subject: %s\r\n' "$subject"
        printf 'Date: %s\r\n' "$(date -R)"
        printf '\r\n'
        cat "$LOG_FILE"
    } > "$msg_file"

    curl --silent --show-error --ssl-reqd \
        --url "smtp://smtp.gmail.com:587" \
        --mail-from "$EMAIL_HOST_USER" \
        --mail-rcpt "$NOTIFY_EMAIL" \
        --user "$EMAIL_HOST_USER:$EMAIL_HOST_PASSWORD" \
        --upload-file "$msg_file" \
        || log "WARNING: failed to send notification email"
}

on_exit() {
    local status=$?
    if [[ $status -eq 0 ]]; then
        notify "[cmn-artist backup] OK $(date +%F)"
    else
        notify "[cmn-artist backup] FAILED $(date +%F)"
    fi
    rm -rf "$WORK_DIR"
}
trap on_exit EXIT

log "Dumping Postgres database..."
DB_DUMP="$WORK_DIR/postgres-${DBNAME}.dump"
docker compose -f "$PROJECT_DIR/docker-compose.yml" exec -T \
    -e PGPASSWORD="$DBPASS" \
    postgres pg_dump -U "$DBUSER" -d "$DBNAME" -F custom -f /tmp/backup.dump

docker compose -f "$PROJECT_DIR/docker-compose.yml" cp \
    postgres:/tmp/backup.dump "$DB_DUMP"

docker compose -f "$PROJECT_DIR/docker-compose.yml" exec -T \
    postgres rm -f /tmp/backup.dump

if [[ ! -s "$DB_DUMP" ]]; then
    log "ERROR: Postgres dump is empty, aborting backup"
    exit 1
fi

log "Backing up to restic repository..."
restic backup \
    "$DB_DUMP" \
    "$MEDIA_DIR" \
    "$NAVIDROME_DATA_DIR" \
    --exclude "$NAVIDROME_DATA_DIR/cache" \
    --host cmn-artist \
    --tag nightly

log "Pruning old snapshots (keep ${KEEP_DAILY}d/${KEEP_WEEKLY}w/${KEEP_MONTHLY}m)..."
restic forget \
    --keep-daily "$KEEP_DAILY" \
    --keep-weekly "$KEEP_WEEKLY" \
    --keep-monthly "$KEEP_MONTHLY" \
    --prune

log "Checking repository integrity..."
restic check

log "Backup complete."
