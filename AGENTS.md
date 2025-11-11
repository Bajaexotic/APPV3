# Repository Guidelines

## Project Structure & Module Organization

- `core/`, `services/`, `panels/`, `widgets/`, `utils/`, `config/` — main Python packages.
- `tests/` — pytest suites mirroring package layout.
- `data/`, `fixtures/`, `logs/` — runtime assets and samples.
- Entrypoint: `main.py`; helper utilities live in `tools/`.
- Use domain‑oriented folders (e.g., `panels/timeframe.py`); files in snake_case.

## Build, Test, and Development Commands

- Create venv: `python -m venv .venv` then `.venv\\Scripts\\Activate.ps1` (PowerShell).
- Install: `pip install -r config/requirements.txt` (or `pip install -e .` if a package is defined).
- Lint/format: `ruff check .` and `ruff format .` (or `black .`).
- Run app: `python main.py`.
- Tests: `pytest -q`; coverage: `pytest -q --cov=.`.

## Coding Style & Naming Conventions

- Python: 4‑space indent; snake_case for functions/vars; PascalCase for classes.
- Keep functions small; prefer pure helpers; avoid magic numbers (centralize in `config/`).
- Keep imports and theme tokens consistent across modules.

## Testing Guidelines

- Place tests in `tests/` mirroring packages; name `test_*.py`.
- Use Arrange–Act–Assert; leverage `fixtures/` for shared data.
- Target ≥80% coverage on changed code; add regression tests for bug fixes.

## Commit & Pull Request Guidelines

- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`.
- Examples:
  - `fix(panel1): prevent plot overlap with timeframe pills`
  - `feat(core): gate theme toolbar via env flag`
- PRs are small and focused with description, linked issues, repro steps, and screenshots for UI changes. Update docs/scripts when interfaces change.

## Change Policy

1. Prefer minimal, reversible changes; explain reasoning inline or in the commit message.
2. Keep imports/theme tokens consistent; avoid magic numbers.
3. If a fix appears to require changes in protected folders or outside the repo, stop and propose.

## Safety & Guardrails

- No network calls unless explicitly requested.
- Never print or commit secrets (env values, tokens); use `.env` and maintain `.env.example`.
- No global/system changes (registry, system env vars, global installs).

## Done Criteria

- App starts cleanly under Run / Repro.
- Tests (if present) pass.
- All edits are confined to `C:\\Users\\cgrah\\Desktop\\APPSIERRA` and outside protected folders.
