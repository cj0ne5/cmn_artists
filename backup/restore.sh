#!/bin/bash
#
# Restore a snapshot from the restic backup repository to a local directory
# for inspection. This does NOT put anything back in place automatically —
# see backup/README.md for how to apply a restored Postgres dump / media /
# Navidrome data back into a running deployment.
#
# Usage:
#   ./restore.sh list                  # list available snapshots
#   ./restore.sh restore <snapshot-id> [target-dir]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${BACKUP_ENV_FILE:-$SCRIPT_DIR/backup.env}"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Missing config: $ENV_FILE (copy backup.env.example and fill it in)" >&2
    exit 1
fi
# shellcheck disable=SC1090
source "$ENV_FILE"
export RESTIC_REPOSITORY RESTIC_PASSWORD B2_ACCOUNT_ID B2_ACCOUNT_KEY

case "${1:-}" in
    list)
        restic snapshots --host cmn-artist
        ;;
    restore)
        SNAPSHOT_ID="${2:?snapshot id required, see: $0 list}"
        TARGET_DIR="${3:-./restored-$SNAPSHOT_ID}"
        mkdir -p "$TARGET_DIR"
        restic restore "$SNAPSHOT_ID" --target "$TARGET_DIR"
        echo "Restored to $TARGET_DIR"
        ;;
    *)
        echo "Usage: $0 list | $0 restore <snapshot-id> [target-dir]" >&2
        exit 1
        ;;
esac
