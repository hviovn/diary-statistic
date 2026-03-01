#!/usr/bin/env python3
"""Check duplicates in a CSV by the `Link` column and report/save results.

Usage:
    python scripts/helper/check_dublicates.py [path/to/sources_legacy_html.csv]

If no path is given the script uses `data/sources_legacy_html.csv`.
"""
import csv
import collections
import os
import sys


def find_duplicates(csv_path):
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return 2

    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    links = [row.get('Link','').strip() for row in rows]
    counter = collections.Counter(links)
    dup_links = [ln for ln,cnt in counter.items() if cnt > 1]

    print(f"Scanning: {csv_path}")
    print(f"Total rows: {len(rows)}")
    print(f"Unique links: {len(counter)}")
    dup_count = sum(counter[ln]-1 for ln in dup_links)
    print(f"Duplicate link count (extra rows): {dup_count}")

    if not dup_links:
        print("No duplicates found.")
        return 0

    print('\nDuplicate links:')
    for ln in sorted(dup_links, key=lambda x: -counter[x]):
        print(f"{counter[ln]:3d}x  {ln}")

    # Save all duplicate rows to a CSV for inspection
    out_path = os.path.splitext(csv_path)[0] + '_duplicates.csv'
    with open(out_path, 'w', newline='', encoding='utf-8') as out:
        writer = None
        written = 0
        for row in rows:
            if row.get('Link','').strip() in dup_links:
                if writer is None:
                    writer = csv.DictWriter(out, fieldnames=list(row.keys()))
                    writer.writeheader()
                writer.writerow(row)
                written += 1

    print(f"Wrote {written} duplicate rows to: {out_path}")
    return 0


def main(argv=None):
    argv = argv or sys.argv[1:]
    csv_path = argv[0] if argv else os.path.join('data', 'sources_legacy_html.csv')
    return find_duplicates(csv_path)


if __name__ == '__main__':
    raise SystemExit(main())
