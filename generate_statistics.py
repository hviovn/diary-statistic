import json
import urllib.request
import re
from datetime import datetime, date, timedelta
import math

def fetch_posts(base_url):
    all_posts = []
    page = 1
    per_page = 100
    while True:
        url = f"{base_url}/wp-json/wp/v2/posts?page={page}&per_page={per_page}"
        print(f"Fetching {url}...")
        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
                if not data:
                    break
                all_posts.extend(data)
                total_pages = int(response.getheader('X-WP-TotalPages', 1))
                if page >= total_pages:
                    break
                page += 1
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            break
    return all_posts

def strip_html(text):
    return re.sub('<[^<]+?>', '', text)

def count_words(text):
    text = strip_html(text)
    words = re.findall(r'\w+', text)
    return len(words)

def process_posts(posts):
    processed_data = {}
    for post in posts:
        date_str = post['date'].split('T')[0]
        title = post['title']['rendered']
        link = post['link']
        content = post['content']['rendered']
        word_count = count_words(content)

        if date_str not in processed_data:
            processed_data[date_str] = []

        processed_data[date_str].append({
            'title': title,
            'link': link,
            'word_count': word_count
        })
    return processed_data

def generate_svg(year, data_by_date, base_url):
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)

    # GitHub grid: 53 weeks, 7 days each
    # Columns: weeks, Rows: days (Mon-Sun)
    # Actually GitHub uses Sun-Sat or Mon-Sun depending on locale. Let's use Sun-Sat.

    # Find the Sunday on or before Jan 1st
    first_sunday = start_date - timedelta(days=(start_date.weekday() + 1) % 7)

    square_size = 10
    square_margin = 2
    width = 53 * (square_size + square_margin) + 40
    height = 7 * (square_size + square_margin) + 30

    svg_parts = [f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" style="background-color: white;">']

    # Day labels
    day_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    for i, label in enumerate(day_labels):
        if i in [1, 3, 5]: # Mon, Wed, Fri
            y = i * (square_size + square_margin) + 27
            svg_parts.append(f'<text x="5" y="{y}" font-family="sans-serif" font-size="8" fill="#767676">{label}</text>')

    # Month labels
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    last_month = -1

    curr = first_sunday
    for week in range(53):
        # Month label logic
        if curr.year == year and curr.month != last_month:
            x = week * (square_size + square_margin) + 30
            svg_parts.append(f'<text x="{x}" y="12" font-family="sans-serif" font-size="8" fill="#767676">{months[curr.month-1]}</text>')
            last_month = curr.month

        for day in range(7):
            if curr > end_date:
                break

            if curr >= start_date:
                date_str = curr.strftime('%Y-%m-%d')
                entries = data_by_date.get(date_str, [])
                count = len(entries)

                color = "#ebedf0" # Empty
                if count > 0:
                    # Scale color based on count (simple version)
                    if count == 1: color = "#9be9a8"
                    elif count == 2: color = "#40c463"
                    elif count == 3: color = "#30a14e"
                    else: color = "#216e39"

                x = week * (square_size + square_margin) + 30
                y = day * (square_size + square_margin) + 18

                tooltip = f"{date_str}: {count} entry" if count == 1 else f"{date_str}: {count} entries"
                if count > 0:
                    tooltip += "\n" + "\n".join([e['title'] for e in entries])

                rect = f'<rect x="{x}" y="{y}" width="{square_size}" height="{square_size}" fill="{color}" rx="2" ry="2"><title>{tooltip}</title></rect>'
                if count == 1:
                    svg_parts.append(f'<a href="{entries[0]["link"]}">{rect}</a>')
                elif count > 1:
                    archive_link = f"{base_url}/{curr.year}/{curr.month:02d}/{curr.day:02d}/"
                    svg_parts.append(f'<a href="{archive_link}">{rect}</a>')
                else:
                    svg_parts.append(rect)

            curr += timedelta(days=1)
        if curr > end_date:
            break

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)

def main():
    base_url = "https://saiht.de/blog"
    posts = fetch_posts(base_url)
    data_by_date = process_posts(posts)

    total_articles = len(posts)
    days_covered = len(data_by_date)
    total_words = sum(e['word_count'] for day in data_by_date.values() for e in day)
    reading_time_minutes = total_words / 200
    reading_time_str = f"{math.floor(reading_time_minutes / 60)}h {math.ceil(reading_time_minutes % 60)}m"

    output = []
    output.append("# Diary Activity Overview\n")

    for year in range(2026, 2005, -1): # Start from 2026 down to 2006
        year_entries = sum(len(entries) for d, entries in data_by_date.items() if d.startswith(str(year)))
        # Show year if there are entries or if it's within the range 2006-2026
        output.append(f"### {year}")
        output.append(generate_svg(year, data_by_date, base_url))
        output.append(f"\n{year_entries} article{'s' if year_entries != 1 else ''} in {year}\n")

    output.append("## Statistics")
    output.append(f"- **Days covered:** {days_covered}")
    output.append(f"- **Total articles:** {total_articles}")
    output.append(f"- **Total words:** {total_words}")
    output.append(f"- **Total reading time:** {reading_time_str}")

    content = "\n".join(output)

    with open("README.md", "r") as f:
        readme = f.read()

    marker_start = "<!-- START_STATS -->"
    marker_end = "<!-- END_STATS -->"

    if marker_start in readme and marker_end in readme:
        new_readme = re.sub(f"{marker_start}.*?{marker_end}", f"{marker_start}\n{content}\n{marker_end}", readme, flags=re.DOTALL)
    else:
        new_readme = readme + f"\n\n{marker_start}\n{content}\n{marker_end}\n"

    with open("README.md", "w") as f:
        f.write(new_readme)

    print("README.md updated.")

if __name__ == "__main__":
    main()
