#!/usr/bin/env bash
set -euo pipefail

# Verifies the Pulse fleet WebSocket command against a running Home Assistant.
# Requires HA_URL and HA_TOKEN in the environment or in a local .env file.

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  source .env
fi

: "${HA_URL:?HA_URL not set}"
: "${HA_TOKEN:?HA_TOKEN not set}"

echo "Checking summary sensors are present..."
for key in cells_low cells_critical cells_without_reading cells_needing_attention; do
  state=$(curl -sf -H "Authorization: Bearer ${HA_TOKEN}" \
    "${HA_URL}/api/states/sensor.${key}" | python3 -c \
    'import json,sys; print(json.load(sys.stdin)["state"])' 2>/dev/null || echo "MISSING")
  printf '  %-26s %s\n' "${key}" "${state}"
done

echo
echo "If every value above is a number, the coordinator is assembling a fleet."
echo "MISSING means the sensor did not register: check the Home Assistant log"
echo "for the oikovis_pulse integration."
