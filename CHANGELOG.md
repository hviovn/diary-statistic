# Changelog

All notable changes to the `diary-statistic` project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]
### Added
- Created `AGENTS.md` guidelines for AI agent workflows and repository conventions.
- Created GitHub Actions workflow (`.github/workflows/deploy-pages.yml`) for automated deployment of `./frontend` to GitHub Pages.
- Created `docs/architecture.md` and `docs/data_pipeline.md` documentation.
- Reorganized web visualization output from `/docs` to `/frontend`.

---

## [0.12.0] - 2026-04-29
### Added
- System uptime heatmap visualization (`PR #52`).
- Integrated `tuptime` SQLite database parsing in `scripts/tuptime/` to record daily system uptime heatmaps (`tuptime.svg` and `tuptime2.svg`).

---

## [0.11.0] - 2026-04-19
### Added
- Web-based source management tool (`PR #51`).
- Added `scripts/manage_sources_web.py`, a Flask-based Single Page Application (SPA) for adding, updating, and deleting sources in `data/sources.yaml` via browser on port 5000.

---

## [0.10.0] - 2026-04-16
### Added
- Combined heatmap view across all years (`PR #49`, `PR #50`).
- Added composite heatmap generator yielding `combined.svg` with 3-column layout for years 1975–2026.
- Preserved native `<title>` tooltips and hyperlink capability per cell in `combined.svg`.

---

## [0.9.0] - 2026-04-14
### Changed
- Refactored pipeline steps and updated web visualization page headers (`PR #47`, `commit 990f678`).

---

## [0.8.0] - 2026-04-11
### Added
- Interactive source menu selection in orchestrator script (`PR #37`, `PR #39`).
- Added `[x]` checklist menu in `scripts/generate_statistics.py` allowing interactive or CLI selection of individual sources for link discovery and extraction.

---

## [0.7.0] - 2026-04-10
### Added
- Coordinate-based persistent tooltip system for web heatmaps (`PR #34`).
- Generated `heatmap_data.json` for precise client-side tooltip alignment on `index.html`.

---

## [0.6.0] - 2026-03-03
### Added
- Support for Legacy HTML crawling and WordPress REST API source extraction (`PR #26`, `PR #29`).
- Introduced source-based color coding in `sources.yaml` with intensity palettes per source.

---

## [0.5.0] - 2026-03-01
### Added
- Utility script `scripts/helper/parse_website_words.py` for on-demand website word count and reading time estimation (`PR #14`).

---

## [0.4.0] - 2026-02-28
### Fixed
- Fixed Jekyll liquid tag parsing errors on GitHub Pages by escaping `{` and `}` as `&#123;` and `&#125;` in SVG tooltips (`PR #9`).
- Split heatmap SVG output per year into `docs/assets/activity_YYYY.svg`.

---

## [0.3.0] - 2026-02-27
### Added
- Initial activity grid heatmap generation (`PR #2`).
- 4-step processing pipeline (`step1_link_discovery.py` through `step4_generate_heatmap.py`).
