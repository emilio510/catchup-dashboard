#!/bin/bash
# Wrapper script for sender cron (polls pending_replies every 2 min)
SCANNER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCANNER_DIR" || exit 1
"$SCANNER_DIR/.venv/bin/python" -m src.sender --config config.yaml 2>&1 >> "$SCANNER_DIR/cron/sender.log"
