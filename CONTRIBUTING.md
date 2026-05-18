# Contributing to Oikovis Pulse

Thanks for your interest. Pulse is in early alpha — APIs, design tokens, and
file layout will change without warning until 0.1.0.

## Development setup

```bash
git clone https://github.com/oikovis/pulse.git
cd pulse
cp .env.example .env       # fill in HA_URL, HA_TOKEN, HA_CONFIG_PATH
cd frontend && pnpm install && pnpm build
```

Requires Node 22, pnpm, Python 3.12.

## Workflow

1. Branch from `dev`.
2. Run `pre-commit install` after cloning.
3. Keep PRs focused — one logical change per PR.
4. CI must be green before review.

## Code style

- Python: `ruff` (config in `pyproject.toml`). Line length 100.
- TypeScript: ESLint + Prettier (Prettier defaults).
- Minimal comments. Explain *why*, not *what*.

## Reporting bugs

Use the issue templates in `.github/ISSUE_TEMPLATE/`.
