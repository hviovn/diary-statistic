# Data Pipeline Specification

The data pipeline processes multiple content sources (WordPress, Quartz, Legacy HTML, GitHub Commits/READMEs) in 4 distinct steps.

---

## Step 1: Link Discovery (`scripts/step1_link_discovery.py`)
- Reads source configurations from `data/sources.yaml`.
- Fetches all available links/entries for configured sources:
  - **WordPress**: Uses REST API (`/wp-json/wp/v2/posts?per_page=100`).
  - **Quartz**: Reads `contentIndex.json` or RSS feed.
  - **Legacy HTML**: Recursively crawls links starting from the root index URL.
  - **GitHub**: Uses GitHub Search API with annual date range partitions (2011 to present) to fetch commit history and README links.
- Writes metadata records to `data/sources_{type}.csv` (`Title`, `Date`, `Link`, `Type`, `Parsed`).
- Implements incremental processing: newly discovered links receive `Parsed=FALSE`, while existing `Parsed=TRUE` rows are preserved.

---

## Step 2: Content Extraction (`scripts/step2_content_extraction.py`)
- Reads `data/sources_{type}.csv`.
- For rows with `Parsed=FALSE`, fetches HTTP response content.
- Strips script/style tags, removes HTML formatting, unescapes HTML entities, normalizes whitespace, and handles character encoding.
- Saves raw text to `data/content_{type}.csv` (`Link`, `Content`).
- Updates `Parsed` column in `sources_{type}.csv` to `TRUE`.

---

## Step 3: Text Analysis & Metrics (`scripts/step3_analysis.py`)
- Reads raw content from `data/content_{type}.csv`.
- Calculates:
  - **Word count**
  - **Sentence count**
  - **Image count**
  - **Reading time**: Calculated at 200 words per minute and formatted as `Xh Ym` (e.g., `0h 34m`).
- Writes aggregations to `data/statistics_{type}.csv` and exports structured JSON summary files to `data/step3_analysis/{source_id}.json`.

---

## Step 4: Heatmap & SVG Generation (`scripts/step4_generate_heatmap.py`)
- Aggregates daily activity metrics across all data sources.
- Generates:
  - Yearly heatmaps in `frontend/assets/activity_{year}.svg`.
  - Color palette legend in `frontend/assets/key.svg`.
  - Composite multi-year overview in `frontend/assets/combined.svg`.
  - Exported dataset in `frontend/assets/heatmap_data.json`.
  - Updated web dashboard in `frontend/index.html`.
  - Injected statistics summary table into `docs/README.md`.
