# System Architecture

The `diary-statistic` project consists of a data acquisition pipeline, a data storage layer, source configuration management interfaces, and static web visualization assets.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    sources.yaml                         │
│  (WordPress, Quartz, Legacy HTML, GitHub Repos/Commits) │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    Data Pipeline                        │
│                                                         │
│  Step 1: Link Discovery (scripts/step1_link_discovery)  │
│  Step 2: Content Extraction (scripts/step2_content_ext) │
│  Step 3: Analysis & Metrics (scripts/step3_analysis.py) │
│  Step 4: Heatmap Generation (scripts/step4_heatmap.py)  │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                  Frontend Web Build                     │
│  frontend/index.html                                    │
│  frontend/assets/activity_YYYY.svg                      │
│  frontend/assets/combined.svg                           │
│  frontend/assets/heatmap_data.json                      │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              GitHub Pages Deployment                    │
│      (.github/workflows/deploy-pages.yml)               │
└─────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Configuration Management
- **`data/sources.yaml`**: Standard configuration file listing all tracked digital content repositories.
- **TUI Source Manager (`scripts/manage_sources.py`)**: Terminal User Interface built with Textual for terminal-based management.
- **Web Source Manager (`scripts/manage_sources_web.py`)**: Web-based Single Page Application built with Flask serving an interactive source editor at `http://localhost:5000`.

### 2. Data Pipeline (`scripts/`)
- Orchestrates link extraction, raw text sanitization, sentence/word/reading time statistics calculations, and SVG generation.
- Utilizes incremental parsing through CSV files (`data/sources_*.csv`, `data/content_*.csv`).

### 3. Web & SVG Frontend (`frontend/`)
- **Yearly SVGs**: Heatmap SVGs for individual years (1975–2026) in 7-row grid formats.
- **Combined SVG (`frontend/assets/combined.svg`)**: 3-column composite layout displaying all years concurrently.
- **Tooltip System**: Direct embedded SVG `<title>` elements for native browser tooltips and coordinate-based JavaScript lookup using `frontend/assets/heatmap_data.json`.
