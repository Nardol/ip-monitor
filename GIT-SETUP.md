# Git Setup Checklist

1) Initialize the repo
- Run: `git init`
- Optional: set identity — `git config user.name "Your Name"`, `git config user.email you@example.com`

2) Review ignore rules
- `.gitignore` added with Python/venv/build/coverage caches and project files.
- Note: `*.yaml` is ignored (to avoid committing local configs). If you need a tracked example, create `config.example.yaml` and add an exception `!config.example.yaml` to `.gitignore`.

3) First commit
- Stage files: `git add .`
- Commit: `git commit -m "chore(repo): init with code, tests, docs, gitignore"`

4) Optional remotes
- Create remote (e.g., GitHub/GitLab), then: `git remote add origin <ssh-or-https-url>`
- Push initial branch: `git branch -M main` then `git push -u origin main`

5) Suggested protections
- Enable branch protection on `main` and require CI checks (ruff + pytest).

6) Quick CI skeleton (optional)
- Lint: `uv run ruff check .`
- Tests: `uv run pytest -q`

7) Pre-commit hooks (recommended)
- Add dev dependency: already listed in `pyproject.toml` (`pre-commit`).
- Install hooks: `uv run pre-commit install`
- Optional pre-push tests: `uv run pre-commit install --hook-type pre-push`
- Run once on all files: `uv run pre-commit run --all-files`
- Keep hooks fresh: `uv run pre-commit autoupdate`

Included hooks
- Formatting: Ruff (official hooks: `astral-sh/ruff-pre-commit`)
- Lint: Ruff (official hooks, with `--fix --exit-non-zero-on-fix`)
- Lockfile: uv lock check (`astral-sh/uv-pre-commit` → `uv-lock`)
- Types: `mypy` (uses project config)
- Hygiene: trailing whitespace, EOF fixer
- Pre-push: `pytest -q` (fast run)
- Commit message lint: Conventional Commits (`compilerla/conventional-pre-commit`) on `commit-msg` with `--strict`.

Commit messages
- Follow Conventional Commits (see `COMMIT_GUIDE.md`).
- Fix a message: `git commit --amend`.
- Bypass (rare): `git commit --no-verify`.
