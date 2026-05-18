<div align="center">

# Pulse

**Beautiful, intelligent device health for Home Assistant.**

[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![HA min](https://img.shields.io/badge/Home%20Assistant-2026.4%2B-03A9F4.svg)](https://www.home-assistant.io)

</div>

> ⚠️ **Alpha.** APIs, design, and behavior will change. Not yet recommended for daily use.

Pulse gives Home Assistant a calm, opinionated view of the health of every
device in your home — batteries, signal, availability, and more. Built as a
custom panel with a polished React UI and a small, async-first Python core.

## Installation

For now, install as a HACS custom repository:

1. HACS → Integrations → ⋮ → Custom repositories
2. Repository: `https://github.com/oikovis/pulse`
3. Category: Integration
4. Install, restart Home Assistant
5. Settings → Devices & Services → Add Integration → "Oikovis Pulse"

A "Pulse" entry will appear in your sidebar.

## Roadmap

- **M0** ✅ Scaffold, custom panel, hello card
- **M1** Release workflow, design system, theme integration
- **M2** Battery discovery and the first real dashboard
- **M3** Notifications, prediction, Battery Notes integration

See [CHANGELOG.md](CHANGELOG.md) for shipped changes.

## License

[MIT](LICENSE) © 2026 Oikovis
