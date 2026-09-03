---
project: Oikovis Pulse
phase: building
stakes: product
season: ""
target: ""
blocker: ""
waiting_on: ""
why: "First public Oikovis product — battery monitoring that's Apple-tier polished and smart by default"
next: "Start M2: design tokens and the battery overview UI, reading the fleet from the oikovis_pulse/fleet websocket command"
effort: 1h
platform: ha-addon
links: {}
steps:
  - "[x] Scaffold, custom panel, and HACS release pipeline (M0)"
  - "[x] Battery discovery data model designed and stress-tested"
  - "[x] Write the M1 implementation plan"
  - "[x] Build M1: battery discovery and data layer"
  - "[x] Verify M1 on a live Home Assistant"
  - "[>] M2: overview UI"
  - "[ ] M3: thresholds, prediction, device detail"
  - "[ ] M4: notifications and polish"
  - "[ ] M5: public v1.0"
---

# Oikovis Pulse

## Open

M0 (foundation scaffold) is done and validated end to end: HACS install,
custom panel, Shadow DOM React render. M1 (battery discovery + data layer)
has a written design, arrived at against real fleet data rather than
assumption, covering unit/cell identity, Battery Notes integration, and
non-replaceable-battery classification. Per-device-class threshold defaults
are explicitly deferred to M3, not silently missing.

M1 is built and RUNNING on the live instance: 187 tests, ruff clean, a pure
data layer (units and cells, Battery Notes enrichment, classification,
persistent identity) exposed over two WebSocket commands and four summary
sensors. No panel UI, as planned.

Verified in Home Assistant on 2026-09-03: 141 units, 151 cells, 49 typed from
Battery Notes, 34 carrying a replaced-date, 7 multi-cell devices. The four
sensors register as sensor.pulse_*. The oikovis_pulse/fleet websocket command
returns the whole fleet as JSON. No errors in the log.

Known: the coordinator only polls every 5 minutes and does not rebuild on
registry changes, so after a Home Assistant restart the fleet is incomplete
for several minutes while integrations load. M2 needs push updates anyway.

M3 must design how rechargeable cells are treated: they are currently excluded
from replace-oriented alerts, so a rechargeable at 5% with no explicit critical
flag is reported nowhere.
