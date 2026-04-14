import json
import os
import math
import yaml
import argparse
import xml.sax.saxutils as saxutils
from datetime import datetime, date, timedelta

def generate_svg(year, data_by_date, source_config, year_stats, include_tooltips=False):
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    first_sunday = start_date - timedelta(days=(start_date.weekday() + 1) % 7)

    max_count = 0
    for d, entries in data_by_date.items():
        if d.startswith(str(year)):
            max_count = max(max_count, len(entries))

    square_size = 10
    square_margin = 2
    width = 53 * (square_size + square_margin) + 40
    # Adjusted height for header and removal of legend
    height = 7 * (square_size + square_margin) + 35

    svg_parts = [f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="background-color: white;">']

    # Header: Year and Statistics
    stats_str = (f"Days documented: {year_stats['total_days']}, "
                 f"Github: {year_stats['github']['days']} ({year_stats['github']['count']}), "
                 f"Quartz: {year_stats['quartz']['days']} ({year_stats['quartz']['count']}), "
                 f"Wordpress: {year_stats['wordpress']['days']} ({year_stats['wordpress']['count']}), "
                 f"Legacy: {year_stats['legacy']['days']} ({year_stats['legacy']['count']})")

    svg_parts.append(f'<text x="5" y="15" font-family="sans-serif" font-size="14" font-weight="bold" fill="#24292e">{year}</text>')
    svg_parts.append(f'<text x="55" y="15" font-family="sans-serif" font-size="9" fill="#767676">{stats_str}</text>')

    day_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    grid_offset_y = 35
    for i, label in enumerate(day_labels):
        if i in [1, 3, 5]:
            y = i * (square_size + square_margin) + grid_offset_y + 9
            svg_parts.append(f'<text x="5" y="{y}" font-family="sans-serif" font-size="8" fill="#767676">{label}</text>')

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    last_month = -1
    curr = first_sunday
    for week in range(53):
        if curr.year == year and curr.month != last_month:
            x = week * (square_size + square_margin) + 30
            svg_parts.append(f'<text x="{x}" y="30" font-family="sans-serif" font-size="8" fill="#767676">{months[curr.month-1]}</text>')
            last_month = curr.month

        for day in range(7):
            if curr > end_date: break
            if curr >= start_date:
                date_str = curr.strftime('%Y-%m-%d')
                entries = data_by_date.get(date_str, [])
                count = len(entries)
                color = "#ebedf0"
                if count > 0:
                    level = math.ceil((count / max_count) * 4) if max_count > 0 else 1
                    sid = entries[0].get('source_id')
                    colors = source_config.get(sid, {}).get('colors', ["#9be9a8", "#40c463", "#30a14e", "#216e39"])
                    color = colors[min(level - 1, len(colors) - 1)]

                x = week * (square_size + square_margin) + 30
                y = day * (square_size + square_margin) + grid_offset_y

                title_tag = ""
                if include_tooltips:
                    tooltip = f"{date_str}: {count} entry" if count == 1 else f"{date_str}: {count} entries"
                    if count > 0:
                        tooltip += "\n" + "\n".join([e['title'] for e in entries])
                    tooltip = saxutils.escape(tooltip).replace('{', '&#123;').replace('}', '&#125;')
                    title_tag = f"<title>{tooltip}</title>"

                rect = f'<rect class="day-cell" data-date="{date_str}" x="{x}" y="{y}" width="{square_size}" height="{square_size}" fill="{color}" rx="2" ry="2">{title_tag}</rect>'
                if count > 0:
                    link = saxutils.quoteattr(entries[0]["url"])
                    svg_parts.append(f'<a href={link}>{rect}</a>')
                else:
                    svg_parts.append(rect)
            curr += timedelta(days=1)
        if curr > end_date: break

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)

def generate_key_svg(source_config):
    # Aggregate by type to get unique names/colors for the key
    types_seen = {}
    for sid, config in source_config.items():
        stype = config['type']
        if stype not in types_seen:
            types_seen[stype] = {
                'name': config['name'],
                'colors': config['colors']
            }

    width = 676
    height = 20
    svg_parts = [f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="background-color: white;">']

    legend_x = 30
    legend_y = 5
    for stype, config in types_seen.items():
        label = config['name']
        colors = config['colors']
        color = colors[2] if len(colors) > 2 else colors[-1]
        svg_parts.append(f'<rect x="{legend_x}" y="{legend_y}" width="8" height="8" fill="{color}" rx="1" ry="1"/>')
        svg_parts.append(f'<text x="{legend_x + 12}" y="{legend_y + 7}" font-family="sans-serif" font-size="7" fill="#767676">{label}</text>')
        legend_x += 70

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tooltip', action='store_true')
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    data_dir = os.path.join(repo_root, 'data')
    analysis_dir = os.path.join(data_dir, 'step3_analysis')
    sources_yaml = os.path.join(data_dir, 'sources.yaml')
    assets_dir = os.path.join(repo_root, 'docs', 'assets')
    os.makedirs(assets_dir, exist_ok=True)

    if not os.path.exists(sources_yaml):
        print("sources.yaml not found.")
        return

    with open(sources_yaml, 'r') as f:
        sources_list = yaml.safe_load(f)

    source_config = {s['id']: s for s in sources_list}
    all_pages = []

    if not os.path.exists(analysis_dir):
        print("Analysis (Step 3) not found.")
        return

    for filename in os.listdir(analysis_dir):
        if not filename.endswith('.json'): continue
        with open(os.path.join(analysis_dir, filename), 'r') as f:
            data = json.load(f)
            for p in data['pages']:
                p['source_id'] = data['source_id']
                all_pages.append(p)

    data_by_date = {}
    total_words = 0
    for p in all_pages:
        d = p['date']
        if not d: continue
        if d not in data_by_date: data_by_date[d] = []
        data_by_date[d].append(p)
        total_words += p['word_count']

    # JSON for web tooltips
    web_heatmap_data = {}
    for d, entries in data_by_date.items():
        web_heatmap_data[d] = [{
            'title': e['title'],
            'link': e['url'],
            'source': source_config.get(e['source_id'], {}).get('name', e['source_id'])
        } for e in entries]

    with open(os.path.join(assets_dir, "heatmap_data.json"), "w") as f:
        json.dump(web_heatmap_data, f, indent=2)

    dates = sorted(data_by_date.keys())
    start_year = 2006
    if dates:
        valid_years = [int(d.split('-')[0]) for d in dates if 1970 <= int(d.split('-')[0]) <= 2026]
        if valid_years: start_year = min(valid_years)
    end_year = 2026

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

    # Key SVG
    key_svg_content = generate_key_svg(source_config)
    with open(os.path.join(assets_dir, "key.svg"), "w") as f:
        f.write(key_svg_content)

    html_output.append('    <div style="margin-bottom: 20px;">')
    html_output.append('        <img src="assets/key.svg" alt="Source key">')
    html_output.append('    </div>')

    # Generate SVGs and collect info for README/index.html
    for year in range(end_year, start_year - 1, -1):
        year_data_by_date = {d: entries for d, entries in data_by_date.items() if d.startswith(str(year))}
        if not year_data_by_date: continue

        # Calculate stats for the year
        year_stats = {
            'total_days': len(year_data_by_date),
            'github': {'days': 0, 'count': 0},
            'quartz': {'days': 0, 'count': 0},
            'wordpress': {'days': 0, 'count': 0},
            'legacy': {'days': 0, 'count': 0}
        }

        type_mapping = {
            'github': 'github',
            'quartz': 'quartz',
            'wordpress': 'wordpress',
            'legacy_html': 'legacy'
        }

        for d, entries in year_data_by_date.items():
            seen_types_today = set()
            for e in entries:
                stype = source_config.get(e['source_id'], {}).get('type')
                mapped_type = type_mapping.get(stype)
                if mapped_type:
                    year_stats[mapped_type]['count'] += 1
                    seen_types_today.add(mapped_type)
            for mt in seen_types_today:
                year_stats[mt]['days'] += 1

        svg_content = generate_svg(year, data_by_date, source_config, year_stats, include_tooltips=args.tooltip)
        svg_filename = f"activity_{year}.svg"
        with open(os.path.join(assets_dir, svg_filename), "w") as f:
            f.write(svg_content)

        svg_with_tooltips = generate_svg(year, data_by_date, source_config, year_stats, include_tooltips=True)
        output.append(svg_with_tooltips)

        html_output.append(f'    <div class="year-section">')
        html_output.append(f'        <div class="heatmap-container" data-year="{year}">')
        html_output.append(f'            <img src="assets/{svg_filename}" alt="Activity heatmap for {year}">')
        html_output.append(f'        </div>')
        html_output.append(f'    </div>')

    # Statistics
    output.append("## Statistics")
    output.append(f"- **Days covered:** {len(data_by_date)}")
    output.append(f"- **Total entries:** {len(all_pages)}")
    output.append(f"- **Total words:** {total_words}")

    html_output.append('    <div class="stats-section">')
    html_output.append("        <h2>Statistics</h2>")
    html_output.append("        <ul>")
    html_output.append(f"            <li><strong>Days covered:</strong> {len(data_by_date)}</li>")
    html_output.append(f"            <li><strong>Total entries:</strong> {len(all_pages)}</li>")
    html_output.append(f"            <li><strong>Total words:</strong> {total_words}</li>")
    html_output.append("        </ul>")
    html_output.append("    </div>")

    # Finalize HTML
    html_output.append("    <script>")
    html_output.append("        const tooltip = document.getElementById('tooltip');")
    html_output.append("        let persistent = false;")
    html_output.append("        let heatmapData = {};")
    html_output.append("        const SQUARE_SIZE = 10; const SQUARE_MARGIN = 2; const OFFSET_X = 30; const OFFSET_Y = 35;")
    html_output.append("        const LOGICAL_WIDTH = 53 * (SQUARE_SIZE + SQUARE_MARGIN) + 40;")
    html_output.append("        const LOGICAL_HEIGHT = 7 * (SQUARE_SIZE + SQUARE_MARGIN) + 35;")
    html_output.append("        fetch('assets/heatmap_data.json').then(r => r.json()).then(d => { heatmapData = d; });")
    html_output.append("        function escapeHTML(str) { const p = document.createElement('p'); p.textContent = str; return p.innerHTML; }")
    html_output.append("        function getInfoAtPosition(container, clientX, clientY) {")
    html_output.append("            const rect = container.getBoundingClientRect();")
    html_output.append("            const scaleX = LOGICAL_WIDTH / rect.width; const scaleY = LOGICAL_HEIGHT / rect.height;")
    html_output.append("            const x = (clientX - rect.left) * scaleX; const y = (clientY - rect.top) * scaleY;")
    html_output.append("            const week = Math.floor((x - OFFSET_X) / (SQUARE_SIZE + SQUARE_MARGIN));")
    html_output.append("            const day = Math.floor((y - OFFSET_Y) / (SQUARE_SIZE + SQUARE_MARGIN));")
    html_output.append("            if (week < 0 || week >= 53 || day < 0 || day >= 7) return null;")
    html_output.append("            const squareLeft = OFFSET_X + week * (SQUARE_SIZE + SQUARE_MARGIN);")
    html_output.append("            const squareTop = OFFSET_Y + day * (SQUARE_SIZE + SQUARE_MARGIN);")
    html_output.append("            if (x < squareLeft || x > squareLeft + SQUARE_SIZE || y < squareTop || y > squareTop + SQUARE_SIZE) return null;")
    html_output.append("            const year = parseInt(container.getAttribute('data-year'));")
    html_output.append("            const startDate = new Date(year, 0, 1);")
    html_output.append("            const firstSunday = new Date(startDate); firstSunday.setDate(startDate.getDate() - startDate.getDay());")
    html_output.append("            const targetDate = new Date(firstSunday); targetDate.setDate(firstSunday.getDate() + (week * 7) + day);")
    html_output.append("            if (targetDate.getFullYear() < year && week === 0) return null;")
    html_output.append("            if (targetDate.getFullYear() > year) return null;")
    html_output.append("            const dateStr = `${targetDate.getFullYear()}-${String(targetDate.getMonth() + 1).padStart(2, '0')}-${String(targetDate.getDate()).padStart(2, '0')}`;")
    html_output.append("            return { dateStr, entries: heatmapData[dateStr] || [], centerX: (squareLeft + SQUARE_SIZE / 2) / scaleX + rect.left, centerY: (squareTop + SQUARE_SIZE / 2) / scaleY + rect.top, cellHeight: SQUARE_SIZE / scaleY };")
    html_output.append("        }")
    html_output.append("        function updateTooltip(info, isPersistent) {")
    html_output.append("            if (!info || info.entries.length === 0) { if (!isPersistent && !persistent) tooltip.style.display = 'none'; return; }")
    html_output.append("            let content = `<strong>${escapeHTML(info.dateStr)}</strong><ul>`;")
    html_output.append("            info.entries.forEach(e => { content += `<li>${escapeHTML(e.source)}: <a href=\"${encodeURI(e.link)}\">${escapeHTML(e.title)}</a></li>`; });")
    html_output.append("            content += '</ul>'; tooltip.innerHTML = content; tooltip.style.display = 'block';")
    html_output.append("            if (isPersistent) { tooltip.classList.add('persistent'); persistent = true; } else { tooltip.classList.remove('persistent'); }")
    html_output.append("            const bodyRect = document.body.getBoundingClientRect();")
    html_output.append("            let left = info.centerX - bodyRect.left - tooltip.offsetWidth / 2;")
    html_output.append("            if (left < 10) left = 10; if (left + tooltip.offsetWidth > bodyRect.width - 10) left = bodyRect.width - tooltip.offsetWidth - 10;")
    html_output.append("            tooltip.style.left = `${left}px`; tooltip.style.setProperty('--arrow-left', `${(info.centerX - bodyRect.left) - left}px`);")
    html_output.append("            let top = info.centerY - bodyRect.top - info.cellHeight / 2 - tooltip.offsetHeight - 12;")
    html_output.append("            if (top < 10) { top = info.centerY - bodyRect.top + info.cellHeight / 2 + 12; tooltip.classList.add('bottom'); } else { tooltip.classList.remove('bottom'); }")
    html_output.append("            tooltip.style.top = `${top}px`;")
    html_output.append("        }")
    html_output.append("        document.addEventListener('mousemove', (e) => {")
    html_output.append("            if (persistent) return;")
    html_output.append("            const container = e.target.closest('.heatmap-container');")
    html_output.append("            if (container) { updateTooltip(getInfoAtPosition(container, e.clientX, e.clientY), false); } else { tooltip.style.display = 'none'; }")
    html_output.append("        });")
    html_output.append("        document.addEventListener('click', (e) => {")
    html_output.append("            const container = e.target.closest('.heatmap-container');")
    html_output.append("            if (container) {")
    html_output.append("                const info = getInfoAtPosition(container, e.clientX, e.clientY);")
    html_output.append("                if (info && info.entries.length > 0) { updateTooltip(info, true); e.preventDefault(); }")
    html_output.append("                else if (!tooltip.contains(e.target)) { tooltip.style.display = 'none'; persistent = false; }")
    html_output.append("            } else if (!tooltip.contains(e.target)) { tooltip.style.display = 'none'; persistent = false; }")
    html_output.append("        });")
    html_output.append("    </script>")
    html_output.append("</body>")
    html_output.append("</html>")

    # Save index.html
    index_path = os.path.join(repo_root, 'docs', 'index.html')
    with open(index_path, 'w') as f:
        f.write("\n".join(html_output))

    # Update README
    readme_path = os.path.join(repo_root, 'docs', 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r') as f:
            readme = f.read()
        marker_start, marker_end = "<!-- START_STATS -->", "<!-- END_STATS -->"
        if marker_start in readme and marker_end in readme:
            start_idx = readme.find(marker_start) + len(marker_start)
            end_idx = readme.find(marker_end)
            new_readme = readme[:start_idx] + "\n" + "\n".join(output) + "\n" + readme[end_idx:]
            with open(readme_path, 'w') as f:
                f.write(new_readme)

    print("Heatmaps, index.html and README updated.")

if __name__ == "__main__":
    main()
