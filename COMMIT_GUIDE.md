# Conventional Commits — Quick Guide

Structure
- `<type>(<scope>)!: <subject>`
- Optional body: why, context, constraints
- Optional footer(s): `BREAKING CHANGE: …`, `Refs #123`, `Fixes #456`

Types (common)
- feat: new user‑facing capability
- fix: bug fix
- docs: documentation only
- refactor: code change without feature/bug
- perf: performance improvement
- test: add/adjust tests only
- chore: tooling, deps, housekeeping
- build/ci/style/revert: as needed

Scopes (suggested for this repo)
- monitoring, config, notify, tests, docs, ci

Rules of thumb
- Subject: imperative, concise (< 72 chars), no trailing period
- Use a scope when it clarifies impact
- Breaking changes: add `!` after scope/type and a `BREAKING CHANGE:` footer

Examples
- `feat(monitoring): default progress prints + --quiet`
- `fix(config): validate db_path writability on existing files`
- `test(notify): cover ntfy/smsbox exception paths`
- `docs: add config.example.yaml instructions`
- `chore(ci): add uv-lock pre-commit hook`

Tips
- Amend after fixes: `git commit --amend`
- If needed (rare), bypass hook: `git commit -m "..." --no-verify`
