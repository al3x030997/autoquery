#!/usr/bin/env bash
# AutoQuery database backup script.
# Usage: ./scripts/backup.sh
# Designed to run via cron on the host machine.
#
# Retention: 7 daily, 4 weekly (Sunday), 3 monthly (1st of month)

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_URL="${DATABASE_URL:-postgresql://autoquery:autoquery@localhost:5432/autoquery}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DAY_OF_WEEK=$(date +%u)  # 1=Monday, 7=Sunday
DAY_OF_MONTH=$(date +%d)

mkdir -p "$BACKUP_DIR"/{daily,weekly,monthly}

DUMP_FILE="$BACKUP_DIR/daily/autoquery_${TIMESTAMP}.dump"

echo "[$(date)] Starting backup..."
pg_dump "$DB_URL" --format=custom --compress=6 --file="$DUMP_FILE"
echo "[$(date)] Backup created: $DUMP_FILE ($(du -h "$DUMP_FILE" | cut -f1))"

# Weekly backup (copy Sunday's daily)
if [ "$DAY_OF_WEEK" = "7" ]; then
    cp "$DUMP_FILE" "$BACKUP_DIR/weekly/autoquery_weekly_${TIMESTAMP}.dump"
    echo "[$(date)] Weekly backup created"
fi

# Monthly backup (copy 1st of month's daily)
if [ "$DAY_OF_MONTH" = "01" ]; then
    cp "$DUMP_FILE" "$BACKUP_DIR/monthly/autoquery_monthly_${TIMESTAMP}.dump"
    echo "[$(date)] Monthly backup created"
fi

# Retention cleanup
echo "[$(date)] Cleaning up old backups..."

# Keep 7 daily
ls -t "$BACKUP_DIR"/daily/*.dump 2>/dev/null | tail -n +8 | xargs -r rm -f

# Keep 4 weekly
ls -t "$BACKUP_DIR"/weekly/*.dump 2>/dev/null | tail -n +5 | xargs -r rm -f

# Keep 3 monthly
ls -t "$BACKUP_DIR"/monthly/*.dump 2>/dev/null | tail -n +4 | xargs -r rm -f

echo "[$(date)] Backup complete."
