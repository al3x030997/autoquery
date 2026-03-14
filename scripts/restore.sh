#!/usr/bin/env bash
# AutoQuery database restore script.
# Usage: ./scripts/restore.sh <backup_file>
#
# WARNING: This will DROP and recreate the target database.

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 backups/daily/autoquery_20260309_030000.dump"
    exit 1
fi

BACKUP_FILE="$1"
DB_URL="${DATABASE_URL:-postgresql://autoquery:autoquery@localhost:5432/autoquery}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "[$(date)] Restoring from: $BACKUP_FILE"
echo "WARNING: This will overwrite the current database. Press Ctrl+C to cancel."
read -r -p "Continue? [y/N] " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Aborted."
    exit 0
fi

echo "[$(date)] Restoring database..."
pg_restore "$DB_URL" --clean --if-exists --no-owner --no-privileges --format=custom "$BACKUP_FILE"

echo "[$(date)] Rebuilding indexes (IVFFlat)..."
psql "$DB_URL" -c "REINDEX DATABASE autoquery;"

echo "[$(date)] Restore complete."
