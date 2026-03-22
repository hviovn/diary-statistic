#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GitHub‑style contribution heatmap from a CSV that contains:
    Title, Word Count, Character count, (and optionally a weblink)

The script assumes the date is stored as the leading "YYYY-MM-DD"
part of the `Title` column (e.g. "2024-03-15 My diary entry").
If your date format differs, adjust DATE_FMT below.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import requests
from io import StringIO

# ----------------------------------------------------------------------
# ⚙️  USER‑CONFIGURABLE SETTINGS# ----------------------------------------------------------------------
CSV_URL = (
    "https://raw.githubusercontent.com/hviovn/diary-statistic/"
    "refs/heads/main/data/statistics_github.csv"
)

# Column that holds the date (as a string you can parse)
DATE_COL = "Title"          # ← change if needed

# Expected date format at the start of the string.
# The CSV uses "YYYY-MM-DD" followed by a space and the entry text.
DATE_FMT = "%Y-%m-%d"

# Metric that drives the colour intensity
METRIC_COL = "Word Count"   # or "Character Count"

# Output file name (set to None to only show the plot)
OUT_FILE = "github_heatmap.png"

# ----------------------------------------------------------------------
# 1️⃣  DOWNLOAD & LOAD THE CSV# ----------------------------------------------------------------------
print(f"Downloading CSV from {CSV_URL} …")
resp = requests.get(CSV_URL)
resp.raise_for_status()   # will raise an error if the download failed

df = pd.read_csv(StringIO(resp.text))
print(f"Loaded {len(df)} rows.")

# ----------------------------------------------------------------------
# 2️⃣  PARSE DATES
# ----------------------------------------------------------------------
# Show a couple of raw values to help debugging if the format ever changes
print("Sample raw date strings:")
print(df[DATE_COL].head(3).tolist())

# Extract the leading YYYY-MM-DD part and convert to datetime.
# We first slice the first 10 characters (the length of "YYYY-MM-DD").
# If a string is shorter than 10 characters we get NaT, which we drop later.
df[DATE_COL] = pd.to_datetime(
    df[DATE_COL].str.slice(0, 10),   # take only the date part
    format=DATE_FMT,
    errors="coerce"
)

before = len(df)
df = df.dropna(subset=[DATE_COL]).copy()
print(f"Dropped {before - len(df)} rows with unparsable dates.")
print(f"Remaining rows: {len(df)}")

# ----------------------------------------------------------------------
# 3️⃣  PREPARE THE METRIC
# ----------------------------------------------------------------------
if METRIC_COL not in df.columns:
    raise KeyError(f"The metric column '{METRIC_COL}' is not present in the CSV.")
df[METRIC_COL] = pd.to_numeric(df[METRIC_COL], errors="coerce").fillna(0)

# ----------------------------------------------------------------------
# 4️⃣  BUILD CALENDAR FIELDS (ISO year, week, weekday)
# ----------------------------------------------------------------------
df["year"] = df[DATE_COL].dt.isocalendar().year
df["week"] = df[DATE_COL].dt.isocalendar().week   # 1‑53
df["weekday"] = df[DATE_COL].dt.weekday          # Monday=0 … Sunday=6

# ----------------------------------------------------------------------
# 5️⃣  AGGREGATE PER DAY (sum – you can change to mean/max/etc.)
# ----------------------------------------------------------------------
daily = (
    df.groupby(["year", "week", "weekday"], as_index=False)
    .agg({METRIC_COL: "sum"})
)

# ----------------------------------------------------------------------
# 6️⃣  PIVOT TO A MATRIX (weekday × week)
# ----------------------------------------------------------------------
# pivot_table accepts fill_value; otherwise we could pivot then .fillna(0)
pivot = df.pivot_table(
    index="weekday",
    columns="week",
    values=METRIC_COL,
    aggfunc="sum",
    fill_value=0
)

# Ensure we have all 7 weekdays (some weeks may be missing a particular day)
pivot = pivot.reindex(range(0, 7), fill_value=0)

# ----------------------------------------------------------------------
# 7️⃣  PLOT THE HEATMAP
# ----------------------------------------------------------------------
sns.set_style("whitegrid")
plt.figure(figsize=(12, 2.5))   # width ≈ #weeks * 0.3, height fixed for 7 days

# GitHub‑like green palette (feel free to change)
cmap = sns.light_palette("#2ea043", as_cmap=True)

ax = sns.heatmap(
    pivot,
    cmap=cmap,
    linewidths=0.5,
    linecolor="gray",
    cbar_kws={"label": METRIC_COL},
    square=False,
)

# ----------------------------------------------------------------------
# 8️⃣  TIDY AXES# ----------------------------------------------------------------------
# Y‑axis: weekday names
weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ax.set_yticklabels(weekday_names, rotation=0, fontsize=9)

# X‑axis: show month ticks for readability (optional but nice)
# Build a mapping week → (year, month) from the original data.
week_to_month = {}
for _, r in df.iterrows():
    w = int(r["week"])
    y = int(r["year"])
    m = r[DATE_COL].month
    if w not in week_to_month:          # keep first occurrence
        week_to_month[w] = (y, m)

# Determine which weeks to label (first week of each month)
ticks = []
tick_labels = []
for week, (yr, mo) in sorted(week_to_month.items()):
    label = f"{mo:02d}\n{yr}"          # e.g. "03\n2024"
    if not tick_labels or tick_labels[-1] != label:
        ticks.append(week)
        tick_labels.append(label)

ax.set_xticks(ticks)
ax.set_xticklabels(tick_labels, rotation=0, fontsize=8)
ax.set_xlabel("Week of year (first week of each month shown)", fontsize=9, labelpad=8)

# Title
plt.title(f"GitHub‑style activity heatmap – {METRIC_COL}", fontsize=12, pad=15)

plt.tight_layout()

# ----------------------------------------------------------------------
# 9️⃣  SAVE / SHOW
# ----------------------------------------------------------------------
if OUT_FILE:
    plt.savefig(OUT_FILE, dpi=300, bbox_inches="tight")
    print(f"Heatmap saved as '{OUT_FILE}'")
else:
    plt.show()
