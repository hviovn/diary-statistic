# AGENTS.md

Welcome to `diary-statistic`! This repository analyzes and visualizes diary, blog, legacy, and repository contribution entries across multiple sources into interactive heatmaps and statistics.

This document provides context, conventions, and instructions for AI agents working in this codebase.

---

## Repository Overview & Layout

- **`data/`**: Configuration and intermediate data files.
  - `data/sources.yaml`: Single source of truth for tracked sources (types, names, base URLs, color palettes, exclusions).
  - `data/sources_*.csv`: Link metadata discovered during Step 1.
  - `data/content_*.csv`: Raw extracted text content from Step 2.
  - `data/statistics_*.csv`: Metrics calculated in Step 3.
  - `data/step3_analysis/`: Per-source JSON structured analysis.
- **`scripts/`**: Executable scripts and python tools.
  - `scripts/generate_statistics.py`: Interactive CLI runner for pipeline execution.
  - `scripts/step1_link_discovery.py`: Discovers links from configured sources (WordPress REST API, Quartz `contentIndex.json`/RSS, Legacy HTML, GitHub Search API).
  - `scripts/step2_content_extraction.py`: Extracts and cleans content for discovered links.
  - `scripts/step3_analysis.py`: Computes statistics (word counts, sentence counts, reading time).
  - `scripts/step4_generate_heatmap.py`: Generates yearly activity SVGs, `key.svg`, `combined.svg`, and exports `frontend/assets/heatmap_data.json` and `frontend/index.html`.
  - `scripts/manage_sources.py`: Textual-based CLI/TUI application for `data/sources.yaml`.
  - `scripts/manage_sources_web.py`: Web-based Flask SPA manager running on port 5000.
  - `scripts/tuptime/`: SQLite processing scripts for system uptime heatmap generation.
- **`frontend/`**: Web visualization assets published to GitHub Pages.
  - Contains `index.html`, `visualization.html`, SVG activity maps in `assets/`, `key.svg`, `combined.svg`, and `heatmap_data.json`.
- **`docs/`**: Project documentation and architecture details.
  - `docs/architecture.md`, `docs/structure.md`, `docs/data_pipeline.md`.
- **`README.md`**: Project overview with embedded SVG activity heatmaps.
- **`CHANGELOG.md`**: Reconstructed history of repository releases and updates.

---

## Key Principles & Conventions

1. **Path Resolution**:
   - Always resolve file paths relative to `repo_root` or script location (e.g. using `os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', ...)`).
   - Generated web output (SVGs, `index.html`, `heatmap_data.json`) must be output to `frontend/` (not `docs/`).
2. **Data Pipeline Incremental Processing**:
   - Step 1 sets `parsed` = `FALSE` for newly discovered links while preserving existing `TRUE` rows.
   - Step 2 reuses content for `TRUE` rows and only fetches content for `FALSE` rows, updating status upon completion.
3. **Heatmap & SVG Conventions**:
   - Standard year heatmaps use height `119` (`7 * (square_size 10 + margin 2) + 35`).
   - Escaping: Curly braces (`{` and `}`) in SVG tooltips must be escaped as HTML entities (`&#123;` and `&#125;`) to avoid Jekyll liquid template processing errors on GitHub Pages.
   - Embed mode (`embed=True` in `generate_svg`) returns `<g>` blocks without XML declaration headers for combined SVG composite assembly (`frontend/assets/combined.svg`).
4. **Reading Time & Stats Formatting**:
   - Reading time is calculated at 200 words per minute.
   - Formatted strictly as `Xh Ym` (e.g. `0h 34m` or `4h 11m`).

---

## Python Environment & Testing

- Dependencies include `PyYAML`, `textual`, and `flask`.
- Ensure scripts run cleanly with `python scripts/step4_generate_heatmap.py` or `python scripts/generate_statistics.py`.

---

## Automated CI/CD

- Pull requests merged into `main` automatically deploy `./frontend` to GitHub Pages via `.github/workflows/deploy-pages.yml`.
