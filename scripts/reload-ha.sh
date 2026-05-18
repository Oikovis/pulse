#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

set -a
# shellcheck disable=SC1091
source "$REPO_ROOT/.env"
set +a

: "${HA_URL:?HA_URL not set in .env}"
: "${HA_TOKEN:?HA_TOKEN not set in .env}"

ENTRY_ID="$(curl -fsS \
  -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/config/config_entries/entry" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(next((e['entry_id'] for e in d if e.get('domain')=='oikovis_pulse'), ''))")"

if [[ -z "$ENTRY_ID" ]]; then
  echo "❌ No oikovis_pulse config entry found" >&2
  exit 1
fi

curl -fsS \
  -X POST \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"entry_id\":\"$ENTRY_ID\"}" \
  "$HA_URL/api/services/homeassistant/reload_config_entry" >/dev/null

echo "✅ Reloaded (entry $ENTRY_ID)"
