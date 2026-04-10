import json
import re
from datetime import datetime, date, timedelta
import math
import os
import xml.sax.saxutils as saxutils
import csv
import sys
import argparse

sys.stdout.reconfigure(encoding='utf-8')

def generate_svg(year, data_by_date, source_config, include_tooltips=False):
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    # first_sunday is the Sunday of the week containing Jan 1st
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

    svg_parts = [f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="background-color: white;">']
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

                    if source_type in source_config:
                        colors = source_config[source_type]['colors']
                        color = colors[min(level - 1, len(colors) - 1)]
                x = week * (square_size + square_margin) + 30
                y = day * (square_size + square_margin) + 18

                title_tag = ""
                if include_tooltips:
                    tooltip = f"{date_str}: {count} entry" if count == 1 else f"{date_str}: {count} entries"
                    if count > 0:
                        tooltip += "\n" + "\n".join([e['title'] for e in entries])
                    tooltip = saxutils.escape(tooltip).replace('{', '&#123;').replace('}', '&#125;')
                    title_tag = f"<title>{tooltip}</title>"

                rect = f'<rect class="day-cell" data-date="{date_str}" x="{x}" y="{y}" width="{square_size}" height="{square_size}" fill="{color}" rx="2" ry="2">{title_tag}</rect>'
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
    for st, config in source_config.items():
        label = config['name']
        colors = config['colors']
        color = colors[2] if len(colors) > 2 else colors[-1]
        svg_parts.append(f'<rect x="{legend_x}" y="{legend_y}" width="8" height="8" fill="{color}" rx="1" ry="1"/>')
        svg_parts.append(f'<text x="{legend_x + 12}" y="{legend_y + 7}" font-family="sans-serif" font-size="7" fill="#767676">{label}</text>')
        legend_x += 70

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)

def main():
    parser = argparse.ArgumentParser(description='Generate heatmaps.')
    parser.add_argument('--tooltip', action='store_true', help='Include tooltips in SVG files')
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), "data")

    sources_file = os.path.join(script_dir, "sources.json")
    with open(sources_file, 'r', encoding='utf-8') as f:
        sources_data_json = json.load(f)

    source_config = {}
    for s in sources_data_json:
        source_config[s['type']] = {
            'name': s.get('name', s['type']),
            'colors': s.get('colors', ["#9be9a8", "#40c463", "#30a14e", "#216e39"])
        }

    all_data = []
    sources = list(source_config.keys())

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

    # Deduplicate by link
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

    # Prepare heatmap data for JSON
    heatmap_json_data = {}
    for date_str, entries in data_by_date.items():
        heatmap_json_data[date_str] = []
        for e in entries:
            heatmap_json_data[date_str].append({
                'title': e['title'],
                'link': e['link'],
                'source': source_config.get(e['source_type'], {}).get('name', e['source_type'])
            })

    with open(os.path.join(assets_dir, "heatmap_data.json"), "w", encoding="utf-8") as f:
        json.dump(heatmap_json_data, f, ensure_ascii=False, indent=2)

    output = ["# Diary Activity Overview\n"]
    html_output = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "    <title>Diary Activity Overview</title>",
        "    <style>",
        "        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; line-height: 1.6; color: #24292e; max-width: 1200px; margin: 0 auto; padding: 20px; position: relative; }",
        "        .heatmap-container { width: 100%; max-width: 1200px; position: relative; cursor: pointer; }",
        "        .heatmap-container img { width: 100%; height: auto; display: block; }",
        "        .year-section { margin-bottom: 40px; }",
        "        .stats-section { margin-top: 50px; border-top: 1px solid #e1e4e8; padding-top: 20px; }",
        "        .source-breakdown { margin-top: 20px; }",
        "        .tooltip {",
        "            position: absolute;",
        "            background: #24292e;",
        "            color: white;",
        "            padding: 12px;",
        "            border-radius: 6px;",
        "            font-size: 12px;",
        "            pointer-events: none;",
        "            z-index: 1000;",
        "            display: none;",
        "            box-shadow: 0 3px 12px rgba(27,31,35,0.15);",
        "            max-width: 300px;",
        "            word-break: break-word;",
        "        }",
        "        .tooltip::after {",
        "            content: '';",
        "            position: absolute;",
        "            bottom: -8px;",
        "            left: var(--arrow-left, 50%);",
        "            margin-left: -8px;",
        "            border-width: 8px 8px 0;",
        "            border-style: solid;",
        "            border-color: #24292e transparent transparent transparent;",
        "        }",
        "        .tooltip.bottom::after {",
        "            bottom: auto;",
        "            top: -8px;",
        "            border-width: 0 8px 8px;",
        "            border-color: transparent transparent #24292e transparent;",
        "        }",
        "        .tooltip.persistent {",
        "            pointer-events: auto;",
        "            display: block;",
        "        }",
        "        .tooltip a {",
        "            color: #58a6ff;",
        "            text-decoration: none;",
        "        }",
        "        .tooltip a:hover {",
        "            text-decoration: underline;",
        "        }",
        "        .tooltip ul {",
        "            list-style: none;",
        "            padding: 0;",
        "            margin: 4px 0 0 0;",
        "        }",
        "        .tooltip li {",
        "            margin-bottom: 2px;",
        "        }",
        "    </style>",
        "</head>",
        "<body>",
        "    <h1>Diary Activity Overview</h1>",
        '    <div id="tooltip" class="tooltip"></div>'
    ]

    source_names = {st: config['name'] for st, config in source_config.items()}

    for year in range(end_year, start_year - 1, -1):
        year_data = [item for d, entries in data_by_date.items() if d.startswith(str(year)) for item in entries]
        year_entries = len(year_data)
        if year_entries == 0: continue

        svg_content = generate_svg(year, data_by_date, source_config, include_tooltips=args.tooltip)
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
        # Always include tooltips for the version inlined in README
        svg_with_tooltips = generate_svg(year, data_by_date, source_config, include_tooltips=True)
        output.append(svg_with_tooltips)

        year_summary = f"{year_entries} article{'s' if year_entries != 1 else ''} in {year}{breakdown_str}"
        output.append(f"\n{year_summary}\n")

        html_output.append(f'    <div class="year-section">')
        html_output.append(f"        <h3>{year}</h3>")
        html_output.append(f'        <div class="heatmap-container" data-year="{year}">')
        html_output.append(f'            <img src="assets/{svg_filename}" alt="Activity heatmap for {year}">')
        html_output.append(f'        </div>')
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
    html_output.append("    <script>")
    html_output.append("        const tooltip = document.getElementById('tooltip');")
    html_output.append("        let persistent = false;")
    html_output.append("        let heatmapData = {};")
    html_output.append("")
    html_output.append("        // SVG constants")
    html_output.append("        const SQUARE_SIZE = 10;")
    html_output.append("        const SQUARE_MARGIN = 2;")
    html_output.append("        const OFFSET_X = 30;")
    html_output.append("        const OFFSET_Y = 18;")
    html_output.append("        const LOGICAL_WIDTH = 53 * (SQUARE_SIZE + SQUARE_MARGIN) + 40;")
    html_output.append("        const LOGICAL_HEIGHT = 7 * (SQUARE_SIZE + SQUARE_MARGIN) + 40;")
    html_output.append("")
    html_output.append("        fetch('assets/heatmap_data.json')")
    html_output.append("            .then(response => response.json())")
    html_output.append("            .then(data => { heatmapData = data; });")
    html_output.append("")
    html_output.append("        function escapeHTML(str) {")
    html_output.append("            const p = document.createElement('p');")
    html_output.append("            p.textContent = str;")
    html_output.append("            return p.innerHTML;")
    html_output.append("        }")
    html_output.append("")
    html_output.append("        function getInfoAtPosition(container, clientX, clientY) {")
    html_output.append("            const rect = container.getBoundingClientRect();")
    html_output.append("            const scaleX = LOGICAL_WIDTH / rect.width;")
    html_output.append("            const scaleY = LOGICAL_HEIGHT / rect.height;")
    html_output.append("            const x = (clientX - rect.left) * scaleX;")
    html_output.append("            const y = (clientY - rect.top) * scaleY;")
    html_output.append("")
    html_output.append("            const week = Math.floor((x - OFFSET_X) / (SQUARE_SIZE + SQUARE_MARGIN));")
    html_output.append("            const day = Math.floor((y - OFFSET_Y) / (SQUARE_SIZE + SQUARE_MARGIN));")
    html_output.append("")
    html_output.append("            if (week < 0 || week >= 53 || day < 0 || day >= 7) return null;")
    html_output.append("")
    html_output.append("            // Precise check if within the square")
    html_output.append("            const squareLeft = OFFSET_X + week * (SQUARE_SIZE + SQUARE_MARGIN);")
    html_output.append("            const squareTop = OFFSET_Y + day * (SQUARE_SIZE + SQUARE_MARGIN);")
    html_output.append("            if (x < squareLeft || x > squareLeft + SQUARE_SIZE || y < squareTop || y > squareTop + SQUARE_SIZE) return null;")
    html_output.append("")
    html_output.append("            // Calculate date from year, week, day")
    html_output.append("            const year = parseInt(container.getAttribute('data-year'));")
    html_output.append("            const startDate = new Date(year, 0, 1);")
    html_output.append("            // Find first Sunday of the week containing Jan 1st")
    html_output.append("            const firstDayOfYear = startDate.getDay(); // 0 = Sun, 1 = Mon...")
    html_output.append("            const firstSunday = new Date(startDate);")
    html_output.append("            firstSunday.setDate(startDate.getDate() - firstDayOfYear);")
    html_output.append("")
    html_output.append("            const targetDate = new Date(firstSunday);")
    html_output.append("            targetDate.setDate(firstSunday.getDate() + (week * 7) + day);")
    html_output.append("")
    html_output.append("            // Check if within the target year boundary")
    html_output.append("            if (targetDate.getFullYear() < year && week === 0) return null;")
    html_output.append("            if (targetDate.getFullYear() > year) return null;")
    html_output.append("")
    html_output.append("            // Form date string manually to avoid timezone issues with toISOString()")
    html_output.append("            const dY = targetDate.getFullYear();")
    html_output.append("            const dM = String(targetDate.getMonth() + 1).padStart(2, '0');")
    html_output.append("            const dD = String(targetDate.getDate()).padStart(2, '0');")
    html_output.append("            const dateStr = `${dY}-${dM}-${dD}`;")
    html_output.append("            const entries = heatmapData[dateStr] || [];")
    html_output.append("")
    html_output.append("            // For tooltip positioning, we need the cell's center in client coordinates")
    html_output.append("            const cellCenterX = (squareLeft + SQUARE_SIZE / 2) / scaleX + rect.left;")
    html_output.append("            const cellCenterY = (squareTop + SQUARE_SIZE / 2) / scaleY + rect.top;")
    html_output.append("            const cellHeight = SQUARE_SIZE / scaleY;")
    html_output.append("")
    html_output.append("            return { dateStr, entries, centerX: cellCenterX, centerY: cellCenterY, cellHeight };")
    html_output.append("        }")
    html_output.append("")
    html_output.append("        function updateTooltip(info, isPersistent) {")
    html_output.append("            if (!info || info.entries.length === 0) {")
    html_output.append("                if (!isPersistent && !persistent) tooltip.style.display = 'none';")
    html_output.append("                return;")
    html_output.append("            }")
    html_output.append("")
    html_output.append("            let content = `<strong>${escapeHTML(info.dateStr)}</strong>`;")
    html_output.append("            content += '<ul>';")
    html_output.append("            info.entries.forEach(entry => {")
    html_output.append("                content += `<li>${escapeHTML(entry.source)}: <a href=\"${encodeURI(entry.link)}\">${escapeHTML(entry.title)}</a></li>`;")
    html_output.append("            });")
    html_output.append("            content += '</ul>';")
    html_output.append("")
    html_output.append("            tooltip.innerHTML = content;")
    html_output.append("            tooltip.style.display = 'block';")
    html_output.append("            if (isPersistent) {")
    html_output.append("                tooltip.classList.add('persistent');")
    html_output.append("                persistent = true;")
    html_output.append("            } else {")
    html_output.append("                tooltip.classList.remove('persistent');")
    html_output.append("            }")
    html_output.append("")
    html_output.append("            const bodyRect = document.body.getBoundingClientRect();")
    html_output.append("            let left = info.centerX - bodyRect.left - tooltip.offsetWidth / 2;")
    html_output.append("            if (left < 10) left = 10;")
    html_output.append("            if (left + tooltip.offsetWidth > bodyRect.width - 10) {")
    html_output.append("                left = bodyRect.width - tooltip.offsetWidth - 10;")
    html_output.append("            }")
    html_output.append("            tooltip.style.left = `${left}px`;")
    html_output.append("")
    html_output.append("            const arrowLeft = (info.centerX - bodyRect.left) - left;")
    html_output.append("            tooltip.style.setProperty('--arrow-left', `${arrowLeft}px`);")
    html_output.append("")
    html_output.append("            let top = info.centerY - bodyRect.top - info.cellHeight / 2 - tooltip.offsetHeight - 12;")
    html_output.append("            if (top < 10) {")
    html_output.append("                top = info.centerY - bodyRect.top + info.cellHeight / 2 + 12;")
    html_output.append("                tooltip.classList.add('bottom');")
    html_output.append("            } else {")
    html_output.append("                tooltip.classList.remove('bottom');")
    html_output.append("            }")
    html_output.append("            tooltip.style.top = `${top}px`;")
    html_output.append("        }")
    html_output.append("")
    html_output.append("        document.addEventListener('mousemove', (e) => {")
    html_output.append("            if (persistent) return;")
    html_output.append("            const container = e.target.closest('.heatmap-container');")
    html_output.append("            if (container) {")
    html_output.append("                const info = getInfoAtPosition(container, e.clientX, e.clientY);")
    html_output.append("                updateTooltip(info, false);")
    html_output.append("            } else {")
    html_output.append("                tooltip.style.display = 'none';")
    html_output.append("            }")
    html_output.append("        });")
    html_output.append("")
    html_output.append("        document.addEventListener('click', (e) => {")
    html_output.append("            const container = e.target.closest('.heatmap-container');")
    html_output.append("            if (container) {")
    html_output.append("                const info = getInfoAtPosition(container, e.clientX, e.clientY);")
    html_output.append("                if (info && info.entries.length > 0) {")
    html_output.append("                    updateTooltip(info, true);")
    html_output.append("                    e.preventDefault();")
    html_output.append("                } else if (!tooltip.contains(e.target)) {")
    html_output.append("                    tooltip.style.display = 'none';")
    html_output.append("                    tooltip.classList.remove('persistent');")
    html_output.append("                    persistent = false;")
    html_output.append("                }")
    html_output.append("            } else if (!tooltip.contains(e.target)) {")
    html_output.append("                tooltip.style.display = 'none';")
    html_output.append("                tooltip.classList.remove('persistent');")
    html_output.append("                persistent = false;")
    html_output.append("            }")
    html_output.append("        });")
    html_output.append("    </script>")
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
    new_content = "\n".join(output)
    if marker_start in readme and marker_end in readme:
        start_idx = readme.find(marker_start) + len(marker_start)
        end_idx = readme.find(marker_end)
        new_readme = readme[:start_idx] + "\n" + new_content + "\n" + readme[end_idx:]
    else:
        new_readme = readme + f"\n\n{marker_start}\n{new_content}\n{marker_end}\n"

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_readme)
    print(f"{readme_path} updated.")

if __name__ == "__main__":
    main()
