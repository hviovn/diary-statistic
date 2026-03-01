import json
import re
from datetime import datetime, date, timedelta
import math
import os
import xml.sax.saxutils as saxutils
import csv
import sys

sys.stdout.reconfigure(encoding='utf-8')

def generate_svg(year, data_by_date):
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    first_sunday = start_date - timedelta(days=(start_date.weekday() + 1) % 7)

    # Calculate max count for the year for intensity reset
    max_count = 0
    for d, entries in data_by_date.items():
        if d.startswith(str(year)):
            max_count = max(max_count, len(entries))

    square_size = 10
    square_margin = 2
    width = 53 * (square_size + square_margin) + 40
    height = 7 * (square_size + square_margin) + 40

    svg_parts = [f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" style="background-color: white;">']
    day_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    for i, label in enumerate(day_labels):
        if i in [1, 3, 5]:
            y = i * (square_size + square_margin) + 27
            svg_parts.append(f'<text x="5" y="{y}" font-family="sans-serif" font-size="8" fill="#767676">{label}</text>')

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    last_month = -1
    curr = first_sunday
    for week in range(53):
        if curr.year == year and curr.month != last_month:
            x = week * (square_size + square_margin) + 30
            svg_parts.append(f'<text x="{x}" y="12" font-family="sans-serif" font-size="8" fill="#767676">{months[curr.month-1]}</text>')
            last_month = curr.month

        for day in range(7):
            if curr > end_date: break
            if curr >= start_date:
                date_str = curr.strftime('%Y-%m-%d')
                entries = data_by_date.get(date_str, [])
                count = len(entries)
                color = "#ebedf0"
                if count > 0:
                    # Intensity level relative to max_count
                    level = math.ceil((count / max_count) * 4) if max_count > 0 else 1
                    source_type = entries[0].get('source_type', 'wordpress')
                    if source_type == 'wordpress': # Green
                        if level == 1: color = "#9be9a8"
                        elif level == 2: color = "#40c463"
                        elif level == 3: color = "#30a14e"
                        else: color = "#216e39"
                    elif source_type == 'quartz': # Red
                        if level == 1: color = "#ffcdd2"
                        elif level == 2: color = "#ef9a9a"
                        elif level == 3: color = "#e57373"
                        else: color = "#ef5350"
                    elif source_type == 'legacy_html': # Blue
                        if level == 1: color = "#bbdefb"
                        elif level == 2: color = "#90caf9"
                        elif level == 3: color = "#64b5f6"
                        else: color = "#42a5f5"
                    elif source_type == 'github': # Orange
                        if level == 1: color = "#fff3e0"
                        elif level == 2: color = "#ffcc80"
                        elif level == 3: color = "#ffa726"
                        else: color = "#fb8c00"
                x = week * (square_size + square_margin) + 30
                y = day * (square_size + square_margin) + 18
                tooltip = f"{date_str}: {count} entry" if count == 1 else f"{date_str}: {count} entries"
                if count > 0:
                    tooltip += "\n" + "\n".join([e['title'] for e in entries])
                tooltip = saxutils.escape(tooltip).replace('{', '&#123;').replace('}', '&#125;')
                rect = f'<rect x="{x}" y="{y}" width="{square_size}" height="{square_size}" fill="{color}" rx="2" ry="2"><title>{tooltip}</title></rect>'
                if count > 0:
                    link = saxutils.quoteattr(entries[0]["link"])
                    svg_parts.append(f'<a href={link}>{rect}</a>')
                else:
                    svg_parts.append(rect)
            curr += timedelta(days=1)
        if curr > end_date: break

    # Add legend
    legend_x = 30
    legend_y = height - 12
    sources_info = [
        ("WordPress", "#30a14e"),
        ("Quartz", "#e57373"),
        ("Legacy HTML", "#64b5f6"),
        ("GitHub", "#ffa726")
    ]
    for label, color in sources_info:
        svg_parts.append(f'<rect x="{legend_x}" y="{legend_y}" width="8" height="8" fill="{color}" rx="1" ry="1"/>')
        svg_parts.append(f'<text x="{legend_x + 12}" y="{legend_y + 7}" font-family="sans-serif" font-size="7" fill="#767676">{label}</text>')
        legend_x += 70

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), "data")

    all_data = []
    sources = ['wordpress', 'quartz', 'legacy_html', 'github']

    for st in sources:
        stats_file = os.path.join(data_dir, f"statistics_{st}.csv")
        if not os.path.exists(stats_file):
            continue
        with open(stats_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                all_data.append({
                    'link': row['Link'],
                    'date': row['Date'],
                    'title': row['Title'],
                    'word_count': int(row['Word Count']),
                    'character_count': int(row['Character Count']),
                    'source_type': st
                })

    # Deduplicate by link (though they should already be mostly unique)
    unique_data = []
    seen_links = set()
    for item in all_data:
        if item['link'] not in seen_links:
            seen_links.add(item['link'])
            unique_data.append(item)
    all_data = unique_data

    data_by_date = {}
    total_words = 0
    for item in all_data:
        d = item['date']
        if d not in data_by_date: data_by_date[d] = []
        data_by_date[d].append(item)
        total_words += item['word_count']

    total_articles = len(all_data)
    days_covered = len(data_by_date)
    reading_time_total_minutes = math.ceil(total_words / 200)
    reading_time_str = f"{reading_time_total_minutes // 60}h {reading_time_total_minutes % 60}m"

    dates = sorted(data_by_date.keys())
    start_year = 2006
    if dates:
        valid_years = [int(d.split('-')[0]) for d in dates if 1970 <= int(d.split('-')[0]) <= 2026]
        if valid_years:
            start_year = min(start_year, min(valid_years))
    end_year = 2026

    assets_dir = os.path.join(os.path.dirname(script_dir), "docs", "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # Source breakdown for whole period
    sources_data = {}
    for item in all_data:
        st = item['source_type']
        if st not in sources_data: sources_data[st] = []
        sources_data[st].append(item)

    output = ["# Diary Activity Overview\n"]
    html_output = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "    <title>Diary Activity Overview</title>",
        "    <style>",
        "        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; line-height: 1.6; color: #24292e; max-width: 900px; margin: 0 auto; padding: 20px; }",
        "        svg { max-width: 100%; height: auto; }",
        "        .year-section { margin-bottom: 40px; }",
        "        .stats-section { margin-top: 50px; border-top: 1px solid #e1e4e8; padding-top: 20px; }",
        "        .source-breakdown { margin-top: 20px; }",
        "    </style>",
        "</head>",
        "<body>",
        "    <h1>Diary Activity Overview</h1>"
    ]

    source_names = {
        'wordpress': 'WordPress',
        'quartz': 'Quartz',
        'legacy_html': 'Legacy HTML',
        'github': 'GitHub'
    }

    for year in range(end_year, start_year - 1, -1):
        year_data = [item for d, entries in data_by_date.items() if d.startswith(str(year)) for item in entries]
        year_entries = len(year_data)
        if year_entries == 0: continue

        svg_content = generate_svg(year, data_by_date)
        svg_filename = f"activity_{year}.svg"
        svg_path = os.path.join(assets_dir, svg_filename)
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

        year_breakdown = {}
        for item in year_data:
            st = item['source_type']
            year_breakdown[st] = year_breakdown.get(st, 0) + 1

        breakdown_parts = []
        for st in sorted(year_breakdown.keys()):
            name = source_names.get(st, st)
            breakdown_parts.append(f"{year_breakdown[st]} {name}")
        breakdown_str = ": " + ", ".join(breakdown_parts) if breakdown_parts else ""

        output.append(f"### {year}")
        output.append(svg_content)
        year_summary = f"{year_entries} article{'s' if year_entries != 1 else ''} in {year}{breakdown_str}"
        output.append(f"\n{year_summary}\n")

        html_output.append(f'    <div class="year-section">')
        html_output.append(f"        <h3>{year}</h3>")
        html_output.append(f"        {svg_content}")
        html_output.append(f"        <p>{year_summary}</p>")
        html_output.append(f'    </div>')

    output.append("## Statistics")
    html_output.append('    <div class="stats-section">')
    html_output.append("        <h2>Statistics</h2>")
    html_output.append("        <ul>")

    output.append(f"- **Days covered:** {days_covered}")
    html_output.append(f"            <li><strong>Days covered:</strong> {days_covered}</li>")
    output.append(f"- **Total entries:** {total_articles}")
    html_output.append(f"            <li><strong>Total entries:</strong> {total_articles}</li>")
    output.append(f"- **Total words:** {total_words}")
    html_output.append(f"            <li><strong>Total words:</strong> {total_words}</li>")
    output.append(f"- **Total reading time:** {reading_time_str}")
    html_output.append(f"            <li><strong>Total reading time:</strong> {reading_time_str}</li>")

    html_output.append("        </ul>")

    output.append("\n### Breakdown by Source")
    html_output.append('        <div class="source-breakdown">')
    html_output.append("            <h3>Breakdown by Source</h3>")
    html_output.append("            <ul>")

    for st, items in sorted(sources_data.items()):
        name = source_names.get(st, st)
        count = len(items)
        words = sum(item['word_count'] for item in items)
        rt_total_min = math.ceil(words / 200)
        rt_str = f"{rt_total_min // 60}h {rt_total_min % 60}m"
        output.append(f"- **{name}:** {count} entries, {words} words, {rt_str} reading time")
        html_output.append(f"                <li><strong>{name}:</strong> {count} entries, {words} words, {rt_str} reading time</li>")

    html_output.append("            </ul>")
    html_output.append("        </div>")

    output.append("\n### Longest 3 articles by source")
    html_output.append('        <div class="longest-articles">')
    html_output.append("            <h3>Longest 3 articles by source</h3>")
    html_output.append("            <ul>")

    for st, items in sorted(sources_data.items()):
        name = source_names.get(st, st)
        top_3 = sorted(items, key=lambda x: x['word_count'], reverse=True)[:3]
        for i, item in enumerate(top_3):
            title = item['title']
            link = item['link']
            wc = item['word_count']
            rt_total_min = math.ceil(wc / 200)
            rt_str = f"{rt_total_min // 60}h {rt_total_min % 60}m"
            output.append(f"- {name} #{i+1}: [{title}]({link}) ({wc} words, {rt_str} reading time)")
            html_output.append(f'                <li>{name} #{i+1}: <a href="{link}">{saxutils.escape(title)}</a> ({wc} words, {rt_str} reading time)</li>')

    html_output.append("            </ul>")
    html_output.append("        </div>")
    html_output.append("    </div>")
    html_output.append("</body>")
    html_output.append("</html>")

    index_path = os.path.join(os.path.dirname(script_dir), "docs", "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html_output))
    print(f"{index_path} generated.")

    readme_path = os.path.join(os.path.dirname(script_dir), "docs", "README.md")
    if not os.path.exists(readme_path):
        os.makedirs(os.path.dirname(readme_path), exist_ok=True)
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write("# Statistics\n\n<!-- START_STATS -->\n<!-- END_STATS -->\n")

    with open(readme_path, "r", encoding="utf-8") as f:
        readme = f.read()

    marker_start, marker_end = "<!-- START_STATS -->", "<!-- END_STATS -->"
    if marker_start in readme and marker_end in readme:
        new_content = "\n".join(output)
        new_readme = re.sub(f"{marker_start}.*?{marker_end}", f"{marker_start}\n{new_content}\n{marker_end}", readme, flags=re.DOTALL)
    else:
        new_content = "\n".join(output)
        new_readme = readme + f"\n\n{marker_start}\n{new_content}\n{marker_end}\n"

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_readme)
    print(f"{readme_path} updated.")

if __name__ == "__main__":
    main()
