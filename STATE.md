---
project: Oikovis Pulse
phase: building
stakes: product
season: ""
target: ""
blocker: "Home Assistant config share not mounted; M1 cannot be deployed or verified"
waiting_on: ""
why: "First public Oikovis product — battery monitoring that's Apple-tier polished and smart by default"
next: "Mount the Home Assistant config share, run ./scripts/deploy-dev.sh, restart HA, then ./scripts/verify-m1.sh - M1 has never run inside Home Assistant"
effort: 1h
platform: ha-addon
links: {}
steps:
  - "[x] Scaffold, custom panel, and HACS release pipeline (M0)"
  - "[x] Battery discovery data model designed and stress-tested"
  - "[x] Write the M1 implementation plan"
  - "[x] Build M1: battery discovery and data layer"
  - "[>] Verify M1 on a live Home Assistant"
  - "[ ] M2: overview UI"
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

M1 is built: 186 tests, ruff clean, a pure data layer (units and cells,
Battery Notes enrichment, classification, persistent identity) exposed over
two WebSocket commands and four summary sensors. No panel UI, as planned.

It has NEVER run inside Home Assistant. The config share was not mounted this
session, so nothing was deployed. Until that happens, every claim about the
integration working is a claim about its tests, not about the app.

M3 must design how rechargeable cells are treated: they are currently excluded
from replace-oriented alerts, so a rechargeable at 5% with no explicit critical
flag is reported nowhere.
