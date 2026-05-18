#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ ! -f "$REPO_ROOT/.env" ]]; then
  echo "❌ Missing .env at $REPO_ROOT/.env (copy from .env.example and fill in)" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source "$REPO_ROOT/.env"
set +a

: "${HA_URL:?HA_URL not set in .env}"
: "${HA_TOKEN:?HA_TOKEN not set in .env}"
: "${HA_CONFIG_PATH:?HA_CONFIG_PATH not set in .env}"

if [[ ! -d "$HA_CONFIG_PATH" ]]; then
  echo "❌ HA config not mounted at $HA_CONFIG_PATH" >&2
  echo "   In Finder: Go → Connect to Server → smb://homeassistant.local/config" >&2
  exit 1
fi

BUNDLE="$REPO_ROOT/custom_components/oikovis_pulse/frontend/pulse.js"
if [[ ! -f "$BUNDLE" ]]; then
  echo "❌ Frontend bundle missing: $BUNDLE" >&2
  echo "   Run: cd frontend && pnpm install && pnpm build" >&2
  exit 1
fi

DEST="$HA_CONFIG_PATH/custom_components/oikovis_pulse/"
mkdir -p "$DEST"

echo "→ Syncing to $DEST"
rsync -av --delete \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  "$REPO_ROOT/custom_components/oikovis_pulse/" "$DEST"

echo "→ Reloading config entry"
ENTRY_ID="$(curl -fsS \
  -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/config/config_entries/entry" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(next((e['entry_id'] for e in d if e.get('domain')=='oikovis_pulse'), ''))")"

if [[ -z "$ENTRY_ID" ]]; then
  echo "ℹ️  No config entry found — add the integration via the HA UI once, then re-run."
  echo "✅ Files synced (no reload performed)"
  exit 0
fi

curl -fsS \
  -X POST \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"entry_id\":\"$ENTRY_ID\"}" \
  "$HA_URL/api/services/homeassistant/reload_config_entry" >/dev/null

echo "✅ Deployed and reloaded (entry $ENTRY_ID)"
