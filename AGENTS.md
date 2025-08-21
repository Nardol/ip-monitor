# Repository Guidelines

## Project Structure & Modules
- Source: `src/ip_monitor/` — core modules: `monitoring.py` (checks, DB, CLI), `config.py` (Pydantic models + YAML loader), `notify.py` (ntfy/smsbox), `__init__.py` (CLI entry `entry_point`).
- Tests: `tests/` — pytest with async support; `tests/conftest.py` provides dummies for optional libs (`aiontfy`, `pysmsboxnet`).
- Config: `config.yaml` example at repo root. Database file defaults to a writable path you choose (e.g., `ipmonitor.db`).

## Build, Test, and Development
- Install deps (dev included): `uv sync --all-groups`
- Run locally: `uv run ip-monitor -c config.yaml`
- Tests + coverage: `uv run pytest -q` (HTML: `htmlcov/index.html`)
- Lint: `uv run ruff check .`
- Types: `uv run mypy`

## Coding Style & Conventions
- Language: Python 3.12, async-first. Indentation: 4 spaces. Prefer small, pure helpers.
- Naming: modules/files `snake_case`; functions/vars `snake_case`; classes `PascalCase`.
- Typing: add type hints; mypy is strict on untyped defs.
- Formatting/Lint: Ruff configured (line length 80, E501 ignored, import sorting enabled). Keep lines short when reasonable.
- Logs/messages: keep existing tone/language consistent (current logs are in French).
 - Progress prints: user-facing prints are enabled by default; use `--quiet` or `IPM_QUIET=1` to silence.

## Testing Guidelines
- Frameworks: pytest, pytest-asyncio, pytest-cov; branch coverage on.
- Threshold: coverage must be ≥ 95% (see `pyproject.toml`).
- Conventions: test files `tests/test_*.py`; functions `test_*`. Use fixtures and the provided dummy modules for notifications.
- Commands: quick run `uv run pytest`; verbose/HTML reports as needed.

## Commit & Pull Requests
- Commits: imperative present, concise subject (< 72 chars), include rationale in body; reference issues like `Refs #123`.
- PRs: include scope, reasoning, tests added/updated, and configuration snippets to reproduce. Ensure `ruff`, `mypy`, and tests pass locally.

## Security & Configuration Tips
- Do not commit real API keys, tokens, or phone numbers; use `.env`/CI secrets. The sample `config.yaml` is for illustration only.
- Ensure the `db_path` directory is writable by the runtime user.
- Runtime requirements: `ping` from iputils in PATH; outbound network access to your targets and notification backends.
- Overrides: prefer CLI/ENV (`IPM_*`) for operational changes without code edits.
