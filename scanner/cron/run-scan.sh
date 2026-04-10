#!/bin/bash
# Wrapper script for launchd cron

SCANNER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_FILE="$SCANNER_DIR/cron/scan.log"

echo "=== Scan started at $(date -u '+%Y-%m-%d %H:%M UTC') ===" >> "$LOG_FILE"

cd "$SCANNER_DIR" || exit 1
"$SCANNER_DIR/.venv/bin/python" -m src.cli --config config.yaml 2>&1 >> "$LOG_FILE"

echo "=== Scan finished at $(date -u '+%Y-%m-%d %H:%M UTC') ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
