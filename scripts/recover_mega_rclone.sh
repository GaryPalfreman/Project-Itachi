#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${ITACHI_MEGA_EMAIL:-}" || -z "${ITACHI_MEGA_PASSWORD:-}" ]]; then
  echo "MEGA recovery credentials are not configured" >&2
  exit 1
fi

export RCLONE_CONFIG="${RUNNER_TEMP:-/tmp}/itachi-rclone.conf"
trap 'rm -f "$RCLONE_CONFIG"' EXIT

rclone config create itachi-mega mega   user "$ITACHI_MEGA_EMAIL"   pass "$(rclone obscure "$ITACHI_MEGA_PASSWORD")"   --non-interactive >/dev/null

mkdir -p data/knowledge
rclone copy "itachi-mega:Project-Itachi/recovery/knowledge" "data/knowledge" --retries 3 --low-level-retries 5
rclone copy "itachi-mega:Project-Itachi/recovery/public_catalog.json" "data" --retries 3 --low-level-retries 5

test -s data/knowledge/public_knowledge.jsonl
echo "Recovered Itachi public knowledge from MEGA"
