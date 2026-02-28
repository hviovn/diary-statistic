import json
import urllib.request
import urllib.parse
import re
from datetime import datetime, date, timedelta
import math
import os
import xml.sax.saxutils as saxutils
import html

def fetch_url(url):
    try:
        # User-Agent to avoid some blocks
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def fetch_wordpress(base_url):
    all_posts = []
    page = 1
    per_page = 100
    while True:
        url = f"{base_url}/wp-json/wp/v2/posts?page={page}&per_page={per_page}"
        print(f"Fetching WordPress: {url}...")
        try:
            content = fetch_url(url)
            if not content: break
            data = json.loads(content)
            if not data:
                break
            for post in data:
                all_posts.append({
                    'date': post['date'].split('T')[0],
                    'title': post['title']['rendered'],
                    'link': post['link'],
                    'content': post['content']['rendered'],
                    'source_type': 'wordpress'
                })
            # Check headers via a separate HEAD or just assume from data length if header not available
            if len(data) < per_page:
                break
            page += 1
        except Exception as e:
            print(f"Error fetching WordPress page {page}: {e}")
            break
    return all_posts

def fetch_quartz(base_url):
    print(f"Fetching Quartz: {base_url}...")
    base_url = base_url.rstrip('/')
    indices = ["/static/contentIndex.json", "/contentIndex.json", "/index.json"]
    content = None
    for idx in indices:
        content = fetch_url(base_url + idx)
        if content: break

    posts = []
    if content:
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                for slug, item in data.items():
                    title = item.get('title', slug)
                    created_date = item.get('date') or item.get('dates', {}).get('created')

                    # Try to extract date from slug if not in metadata
                    if not created_date:
                        # Match YYYY/MM/DD or YYYY-MM-DD
                        date_match = re.search(r'(\d{4})[/-](\d{2})[/-](\d{2})', slug)
                        if date_match:
                            created_date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
                        else:
                            # Match YYYY/MM (assume 01 for day)
                            date_match = re.search(r'(\d{4})[/-](\d{2})', slug)
                            if date_match:
                                created_date = f"{date_match.group(1)}-{date_match.group(2)}-01"
                            else:
                                # Match YYYY in slug
                                date_match = re.search(r'\b(\d{4})\b', slug)
                                if date_match:
                                    created_date = f"{date_match.group(1)}-01-01"

                    # Try content for lines like "2025-10-20"
                    if not created_date:
                        content = item.get('content', '')
                        date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', content)
                        if date_match:
                            created_date = date_match.group(1)

                    # Special case for filePath if slug doesn't have it
                    if not created_date and 'filePath' in item:
                        date_match = re.search(r'(\d{4})[/-](\d{2})[/-](\d{2})', item['filePath'])
                        if date_match:
                            created_date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"

                    if created_date:
                        created_date = created_date.split('T')[0]
                        link = f"{base_url}/{slug.lstrip('/')}"
                        link = link.replace('https://https://', 'https://')
                        posts.append({
                            'date': created_date,
                            'title': title,
                            'link': link,
                            'content': item.get('content', ''),
                            'source_type': 'quartz'
                        })
        except Exception as e:
            print(f"Error parsing Quartz index: {e}")

    print("Fetching Quartz RSS fallback...")
    rss_url = base_url + "/index.xml"
    rss_content = fetch_url(rss_url)
    if rss_content:
        items = re.findall(r'<item>(.*?)</item>', rss_content, re.DOTALL)
        for item in items:
            title_match = re.search(r'<title>(.*?)</title>', item)
            link_match = re.search(r'<link>(.*?)</link>', item)
            pub_date_match = re.search(r'<pubDate>(.*?)</pubDate>', item)
            if title_match and link_match and pub_date_match:
                try:
                    title = title_match.group(1)
                    link = link_match.group(1).replace('https://https://', 'https://')
                    date_match = re.search(r'\d{1,2} \w{3} \d{4}', pub_date_match.group(1))
                    if date_match:
                        d = datetime.strptime(date_match.group(0), "%d %b %Y")
                        date_str = d.strftime('%Y-%m-%d')
                        if not any(p['link'] == link for p in posts):
                            posts.append({
                                'date': date_str,
                                'title': title,
                                'link': link,
                                'content': '',
                                'source_type': 'quartz'
                            })
                except Exception as e:
                    print(f"Error parsing RSS item: {e}")
    return posts

def fetch_github(username):
    print(f"Fetching GitHub commits for user: {username}...")
    all_commits = []
    page = 1
    per_page = 100

    # We use the search API to find commits by the user.
    # Note: This requires specific headers and might be subject to lower rate limits.
    while page <= 10: # Limit to 10 pages to avoid deep paging issues and stay within reasonable limits
        # Sort by committer-date to get a consistent order
        url = f"https://api.github.com/search/commits?q=author:{username}&sort=committer-date&order=desc&page={page}&per_page={per_page}"
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/vnd.github.cloak-preview' # Required for commit search API
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read().decode('utf-8', errors='ignore')
                data = json.loads(content)

                if not data.get('items'):
                    break

                for item in data['items']:
                    commit_date = item['commit']['author']['date'].split('T')[0]
                    repo_name = item['repository']['full_name']
                    msg = item['commit']['message'].split('\n')[0]
                    all_commits.append({
                        'date': commit_date,
                        'title': f"[{repo_name}] {msg}",
                        'link': item['html_url'],
                        'content': item['commit']['message'], # Use message as content for word count
                        'source_type': 'github'
                    })

                if len(data['items']) < per_page or len(all_commits) >= 1000: # Limit to 1000 for now to avoid hitting limits
                    break
                page += 1
        except Exception as e:
            print(f"Error fetching GitHub commits: {e}")
            break

    return all_commits

def fetch_legacy_html(base_url):
    print(f"Fetching Legacy HTML: {base_url}...")
    base_url = base_url.rstrip('/') + '/'
    to_visit = [base_url]
    visited = set()
    posts = []

    date_patterns = [
        (r'\b(\d{4}-\d{2}-\d{2})\b', '%Y-%m-%d'),
        (r'\b(\d{2}\.\d{2}\.\d{4})\b', '%d.%m.%Y'),
        (r'\b([A-Z][a-z]+ \d{1,2}, \d{4})\b', '%B %d, %Y'),
        (r'\b(\d{1,2}\. [A-Z][a-z]+ \d{4})\b', '%d. %B %Y')
    ]

    while to_visit and len(visited) < 300:
        url = to_visit.pop(0)
        url_no_frag = url.split('#')[0]
        if url_no_frag in visited: continue
        visited.add(url_no_frag)

        content = fetch_url(url_no_frag)
        if not content: continue

        found_date_str = None
        date_obj = None
        for pattern, fmt in date_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    date_obj = datetime.strptime(match.group(1), fmt)
                    found_date_str = date_obj.strftime('%Y-%m-%d')
                    break
                except:
                    continue

        title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1) if title_match else url_no_frag.split('/')[-1]
        title = re.sub('<[^<]+?>', '', title).strip()

        if found_date_str and not url_no_frag.endswith(('index.html', 'navigator.html', 'rechts.html')):
            posts.append({
                'date': found_date_str,
                'title': title,
                'link': url_no_frag,
                'content': content,
                'source_type': 'legacy_html'
            })

        links = re.findall(r'href=["\'](.*?)["\']', content)
        for link in links:
            abs_link = urllib.parse.urljoin(url_no_frag, link).split('#')[0]
            if abs_link.startswith(base_url) and abs_link not in visited:
                if not abs_link.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.doc', '.css', '.js')):
                    to_visit.append(abs_link)

    return posts

def strip_html(text):
    # Remove script and style tags and their content
    text = re.sub(r'<(script|style).*?>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove other HTML tags
    text = re.sub('<[^<]+?>', '', text)
    # Unescape common entities
    text = html.unescape(text)
    return text

def count_words(text):
    text = strip_html(text)
    words = re.findall(r'\w+', text)
    return len(words)

def generate_svg(year, data_by_date):
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    first_sunday = start_date - timedelta(days=(start_date.weekday() + 1) % 7)

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
                    source_type = entries[0].get('source_type', 'wordpress')
                    if source_type == 'wordpress': # Green
                        if count == 1: color = "#9be9a8"
                        elif count == 2: color = "#40c463"
                        elif count == 3: color = "#30a14e"
                        else: color = "#216e39"
                    elif source_type == 'quartz': # Red
                        if count == 1: color = "#ffcdd2"
                        elif count == 2: color = "#ef9a9a"
                        elif count == 3: color = "#e57373"
                        else: color = "#ef5350"
                    elif source_type == 'legacy_html': # Blue
                        if count == 1: color = "#bbdefb"
                        elif count == 2: color = "#90caf9"
                        elif count == 3: color = "#64b5f6"
                        else: color = "#42a5f5"
                    elif source_type == 'github': # Teal
                        if count == 1: color = "#b2dfdb"
                        elif count == 2: color = "#80cbc4"
                        elif count == 3: color = "#4db6ac"
                        else: color = "#26a69a"
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
        ("GitHub", "#4db6ac")
    ]
    for label, color in sources_info:
        svg_parts.append(f'<rect x="{legend_x}" y="{legend_y}" width="8" height="8" fill="{color}" rx="1" ry="1"/>')
        svg_parts.append(f'<text x="{legend_x + 12}" y="{legend_y + 7}" font-family="sans-serif" font-size="7" fill="#767676">{label}</text>')
        legend_x += 70

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sources_file = os.path.join(script_dir, "sources.json")
    with open(sources_file, "r") as f:
        sources = json.load(f)

    all_data = []
    for source in sources:
        if source['type'] == 'wordpress': all_data.extend(fetch_wordpress(source['url']))
        elif source['type'] == 'quartz': all_data.extend(fetch_quartz(source['url']))
        elif source['type'] == 'legacy_html': all_data.extend(fetch_legacy_html(source['url']))
        elif source['type'] == 'github': all_data.extend(fetch_github(source['url']))

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
        item['word_count'] = count_words(item.get('content', ''))
        d = item['date']
        if d not in data_by_date: data_by_date[d] = []
        data_by_date[d].append(item)
        total_words += item['word_count']

    total_articles = len(all_data)
    days_covered = len(data_by_date)
    reading_time_minutes = total_words / 200
    reading_time_str = f"{math.floor(reading_time_minutes / 60)}h {math.ceil(reading_time_minutes % 60)}m"

    dates = sorted(data_by_date.keys())
    start_year = 2006 # Default start year
    if dates:
        # Filter out clearly invalid dates like "0001-01-01" or far-future dates
        valid_years = [int(d.split('-')[0]) for d in dates if 1970 <= int(d.split('-')[0]) <= 2026]
        if valid_years:
            start_year = min(start_year, min(valid_years))
    end_year = 2026

    assets_dir = os.path.join(os.path.dirname(script_dir), "docs", "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # Generate CSV files for each source
    sources_data = {}
    for item in all_data:
        st = item.get('source_type', 'unknown')
        if st not in sources_data: sources_data[st] = []
        sources_data[st].append(item)

    for st, items in sources_data.items():
        csv_filename = f"source_{st}.csv"
        csv_path = os.path.join(assets_dir, csv_filename)
        with open(csv_path, "w") as f:
            f.write("Title,Link,Word Count\n")
            for item in items:
                title = item['title'].replace('"', '""')
                link = item['link']
                wc = item['word_count']
                f.write(f'"{title}","{link}",{wc}\n')
        print(f"Generated {csv_path}")

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

    for year in range(end_year, start_year - 1, -1):
        year_entries = sum(len(entries) for d, entries in data_by_date.items() if d.startswith(str(year)))
        svg_content = generate_svg(year, data_by_date)
        svg_filename = f"activity_{year}.svg"
        svg_path = os.path.join(assets_dir, svg_filename)
        with open(svg_path, "w") as f:
            f.write(svg_content)

        output.append(f"### {year}")
        output.append(svg_content)
        output.append(f"\n{year_entries} article{'s' if year_entries != 1 else ''} in {year}\n")

        html_output.append(f'    <div class="year-section">')
        html_output.append(f"        <h3>{year}</h3>")
        html_output.append(f"        {svg_content}")
        html_output.append(f"        <p>{year_entries} article{'s' if year_entries != 1 else ''} in {year}</p>")
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

    source_names = {
        'wordpress': 'WordPress',
        'quartz': 'Quartz',
        'legacy_html': 'Legacy HTML',
        'github': 'GitHub'
    }
    for st, items in sorted(sources_data.items()):
        name = source_names.get(st, st)
        count = len(items)
        words = sum(item.get('word_count', 0) for item in items)
        output.append(f"- **{name}:** {count} entries, {words} words")
        html_output.append(f"                <li><strong>{name}:</strong> {count} entries, {words} words</li>")

    html_output.append("            </ul>")
    html_output.append("        </div>")
    html_output.append("    </div>")
    html_output.append("</body>")
    html_output.append("</html>")

    # Save index.html
    index_path = os.path.join(os.path.dirname(script_dir), "docs", "index.html")
    with open(index_path, "w") as f:
        f.write("\n".join(html_output))
    print(f"{index_path} generated.")

    readme_path = os.path.join(os.path.dirname(script_dir), "docs", "README.md")
    if not os.path.exists(readme_path):
        os.makedirs(os.path.dirname(readme_path), exist_ok=True)
        with open(readme_path, "w") as f:
            f.write("# Statistics\n\n<!-- START_STATS -->\n<!-- END_STATS -->\n")

    with open(readme_path, "r") as f:
        readme = f.read()

    marker_start, marker_end = "<!-- START_STATS -->", "<!-- END_STATS -->"
    if marker_start in readme and marker_end in readme:
        new_content = "\n".join(output)
        new_readme = re.sub(f"{marker_start}.*?{marker_end}", f"{marker_start}\n{new_content}\n{marker_end}", readme, flags=re.DOTALL)
    else:
        new_content = "\n".join(output)
        new_readme = readme + f"\n\n{marker_start}\n{new_content}\n{marker_end}\n"

    with open(readme_path, "w") as f:
        f.write(new_readme)
    print(f"{readme_path} updated.")

if __name__ == "__main__":
    main()
