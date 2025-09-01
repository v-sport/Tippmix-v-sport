#!/usr/bin/env bash
# Simple runner script: futtatja a poll módot és logolja az outputot
# Futtatás: bash scripts/run_poller.sh
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE_DIR" || exit 1

LOG="$BASE_DIR/poller.log"
# -u: unbuffered Python output
nohup python -u -m scraper.cli poll >> "$LOG" 2>&1 &
echo "Started poller, log: $LOG"
echo "PID: $!"