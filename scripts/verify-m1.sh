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

fetch_state() {
  # $1: entity id. Prints the state, or nothing if unavailable.
  curl -sf -H "Authorization: Bearer ${HA_TOKEN}" \
    "${HA_URL}/api/states/$1" | python3 -c \
    'import json,sys; print(json.load(sys.stdin)["state"])' 2>/dev/null
}

echo "Checking summary sensors are present..."
for key in cells_low cells_critical cells_without_reading cells_needing_attention; do
  # _attr_has_entity_name mints sensor.pulse_<key>; fall back to the bare
  # sensor.<key> id in case the device is ever named differently.
  entity_id="sensor.pulse_${key}"
  state=$(fetch_state "${entity_id}")
  if [[ -z "${state}" ]]; then
    entity_id="sensor.${key}"
    state=$(fetch_state "${entity_id}")
  fi
  if [[ -z "${state}" ]]; then
    entity_id="-"
    state="MISSING"
  fi
  printf '  %-26s %-30s %s\n' "${key}" "${entity_id}" "${state}"
done

echo
echo "If every value above is a number, the coordinator is assembling a fleet."
echo "MISSING means the sensor did not register: check the Home Assistant log"
echo "for the oikovis_pulse integration."
