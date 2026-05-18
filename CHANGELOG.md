# Changelog

All notable changes to Oikovis Pulse are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Notes for M1
- Release workflow: build `pulse.js` in CI and attach to GitHub Releases so HACS installs ship a working bundle.

## [0.0.1] - 2026-05-18

### Added
- Project scaffold (M0).
- Custom panel registered in the HA sidebar as "Pulse".
- React 18 + Vite + TypeScript + Tailwind v4 frontend, bundled to a single ES module.
- Config flow with single-instance enforcement.
