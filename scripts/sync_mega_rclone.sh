#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${ITACHI_MEGA_EMAIL:-}" || -z "${ITACHI_MEGA_PASSWORD:-}" ]]; then
  echo "MEGA recovery mirror not configured"
  exit 0
fi

export RCLONE_CONFIG="${RUNNER_TEMP:-/tmp}/itachi-rclone.conf"
trap 'rm -f "$RCLONE_CONFIG"' EXIT

rclone config create itachi-mega mega   user "$ITACHI_MEGA_EMAIL"   pass "$(rclone obscure "$ITACHI_MEGA_PASSWORD")"   --non-interactive >/dev/null

rclone mkdir "itachi-mega:Project-Itachi/recovery"
rclone copy "data/public_catalog.json" "itachi-mega:Project-Itachi/recovery" --retries 3 --low-level-retries 5
rclone copy "data/knowledge" "itachi-mega:Project-Itachi/recovery/knowledge" --retries 3 --low-level-retries 5

echo "MEGA recovery mirror updated"
