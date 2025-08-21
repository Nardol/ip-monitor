# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2025-08-21
### Added
- config: Use platformdirs to resolve standard paths (user_config_dir, site_config_dir, user_data_dir).
- tests: Add coverage for config discovery order and default `db_path`.
- docs: Document default paths and server deployment, including systemd `IPM_CONFIG` example.

### Changed
- Default config discovery order is now:
  1) `IPM_CONFIG` env var
  2) `./config.yaml`
  3) `${user_config_dir}/ip-monitor/config.yaml`
  4) `${site_config_dir}/ip-monitor/config.yaml` (e.g. `/etc/xdg/ip-monitor/config.yaml`)
  5) Linux fallback: `/etc/ip-monitor/config.yaml`
- Default `db_path` now points to `${user_data_dir}/ip-monitor/ipmonitor.db` (parent dir created if needed) when not specified in YAML/CLI.

### Dependencies
- Add `platformdirs` as a runtime dependency.

## [1.0.0] - 2024-09-13
- Initial Python port with asyncio, SQLite persistence, and ntfy/smsbox notifications.
