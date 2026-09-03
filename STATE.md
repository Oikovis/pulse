---
project: Oikovis Pulse
phase: building
stakes: product
season: ""
target: ""
blocker: ""
waiting_on: ""
why: "First public Oikovis product — battery monitoring that's Apple-tier polished and smart by default"
next: "Open the M1 battery-discovery data-model spec (local, docs/superpowers/specs/) and invoke writing-plans for the M1 implementation plan"
effort: deep
platform: ha-addon
links: {}
steps:
  - "[x] Scaffold, custom panel, and HACS release pipeline (M0)"
  - "[x] Battery discovery data model designed and stress-tested"
  - "[>] Write the M1 implementation plan"
  - "[ ] Build M1: battery discovery and data layer"
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

Next real step is turning that design into an implementation plan, then
building M1. No panel UI work happens until M2.
