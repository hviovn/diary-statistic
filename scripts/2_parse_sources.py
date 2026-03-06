import json
import urllib.request
import re
import os
import csv
import html
import sys
import platform

try:
    import msvcrt
except Exception:
    msvcrt = None
try:
    import tty
    import termios
except Exception:
    tty = None
    termios = None

# Increase the CSV field size limit for large content
csv.field_size_limit(sys.maxsize)

def get_encoding(response):
    """Detect encoding from response headers."""
    content_type = response.headers.get('Content-Type', '')
    if 'charset=' in content_type:
        return content_type.split('charset=')[-1].strip()
    return 'utf-8'

def fetch_url(url):
    """Fetch content from URL and decode using appropriate encoding."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            encoding = get_encoding(response)
            raw_data = response.read()
            try:
                return raw_data.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                # Fallback to common encodings
                for fallback in ['utf-8', 'iso-8859-1', 'cp1252']:
                    try:
                        return raw_data.decode(fallback)
                    except UnicodeDecodeError:
                        continue
                return raw_data.decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def strip_html(text):
    """Remove HTML markers and unescape entities."""
    if not text:
        return ""
    # Remove script and style tags and their content
    text = re.sub(r'<(script|style).*?>.*?</\1>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove other HTML tags, replacing them with a space
    text = re.sub('<[^<]+?>', ' ', text)
    # Unescape HTML entities
    text = html.unescape(text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def fetch_github_content(link, source_type):
    """Extract content from GitHub commits or READMEs with rate limiting check."""
    if source_type == 'github commit':
        match = re.search(r'github\.com/([^/]+/[^/]+)/commit/([0-9a-f]+)', link)
        if match:
            repo = match.group(1)
            sha = match.group(2)
            api_url = f"https://api.github.com/repos/{repo}/commits/{sha}"
            token = os.environ.get('GITHUB_TOKEN')
            headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.github.v3+json'}
            if token:
                headers['Authorization'] = f'token {token}'
            try:
                req = urllib.request.Request(api_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    # Check for rate limiting in headers if possible
                    remaining = response.headers.get('X-RateLimit-Remaining')
                    if remaining and int(remaining) == 0:
                        print(f"Warning: GitHub API rate limit reached.")
                        return ""
                    data = json.loads(response.read().decode('utf-8'))
                    return data['commit']['message']
            except urllib.error.HTTPError as e:
                if e.code == 403:
                    print(f"GitHub API Error 403: Possibly rate limited.")
                else:
                    print(f"Error fetching github commit content for {link}: {e}")
                return ""
            except Exception as e:
                print(f"Error fetching github commit content for {link}: {e}")
                return ""
    elif source_type == 'github readme':
        raw_link = link.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
        content = fetch_url(raw_link)
        return strip_html(content)
    return ""

def process_csv(source_type, data_dir, selected_urls=None):
    """Read sources CSV and generate content CSV."""
    input_file = os.path.join(data_dir, f"sources_{source_type}.csv")
    output_file = os.path.join(data_dir, f"content_{source_type}.csv")

    if not os.path.exists(input_file):
        print(f"Input file {input_file} not found.")
        return

    # Load existing content to reuse
    content_map = {}
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                content_map[row['Link']] = row['Content']

    print(f"Processing {input_file}...")
    updated_sources = []
    content_results = []

    with open(input_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = reader.fieldnames
        for row in reader:
            link = row['Link']
            row_type = row['Type']
            title = row.get('Title', '')
            is_parsed = row.get('parsed') == 'TRUE'

            # Filter by selected urls if provided
            should_process = True
            if selected_urls:
                should_process = False
                for url in selected_urls:
                    match_url = url
                    if source_type == "github" and not url.startswith("http"):
                        match_url = f"https://github.com/{url}/"
                    if link.startswith(match_url):
                        should_process = True
                        break

            content = ""
            if is_parsed and link in content_map:
                print(f"  Skipping {link} (already parsed)...")
                content = content_map[link]
            elif should_process:
                print(f"  Processing {link}...")
                if source_type in ['wordpress', 'quartz', 'legacy_html']:
                    raw_content = fetch_url(link)
                    content = strip_html(raw_content)
                elif source_type == 'github':
                    if row_type == 'github commit':
                        # Use commit message from title to avoid API rate limiting
                        # Title format: "[repo] message"
                        content = re.sub(r'^\[.*?\]\s*', '', title)
                    else:
                        content = fetch_github_content(link, row_type)

                if content:
                    row['parsed'] = 'TRUE'
            else:
                # Not selected for processing, but we should preserve existing content if available
                content = content_map.get(link, "")

            updated_sources.append(row)
            content_results.append({
                'Link': link,
                'Content': content
            })

    # Update sources CSV with parsed status
    with open(input_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in updated_sources:
            writer.writerow(row)

    # Save content CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames_content = ['Link', 'Content']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames_content)
        writer.writeheader()
        for row in content_results:
            # Only save the necessary fields
            writer.writerow({k: row[k] for k in fieldnames_content})
    print(f"Saved to {output_file}")

def _getch():
    if msvcrt:
        return msvcrt.getch()
    else:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
            return ch.encode()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def interactive_selection(sources, title=None):
    idx = 0
    selected = [False] * len(sources)
    while True:
        # clear screen
        if os.name == 'nt':
            os.system('cls')
        else:
            os.system('clear')

        if title:
            print(title)
        print('Use Up/Down arrows to navigate, Space to toggle, Enter to confirm. Ctrl-C to cancel.')
        for i, source in enumerate(sources):
            prefix = '=> ' if i == idx else '   '
            mark = '[x]' if selected[i] else '[ ]'
            name = source.get('name', source['type'])
            url = source['url']
            print(f"{prefix}{mark} {name} ({url})")

        try:
            ch = _getch()
        except Exception:
            print('\nInput error; falling back to numeric selection.')
            for i, source in enumerate(sources):
                name = source.get('name', source['type'])
                print(f"{i+1}. {name}")
            try:
                choice = input('Enter numbers separated by comma: ')
                choices = [int(c.strip()) - 1 for c in choice.split(',') if c.strip()]
                return [c for c in choices if 0 <= c < len(sources)]
            except Exception:
                return None

        # Windows msvcrt
        if msvcrt:
            if ch in (b'\r', b'\n'):
                return [i for i, s in enumerate(selected) if s]
            if ch == b' ':
                selected[idx] = not selected[idx]
            if ch in (b'\x00', b'\xe0'):
                ch2 = msvcrt.getch()
                if ch2 == b'H': # Up
                    idx = (idx - 1) % len(sources)
                elif ch2 == b'P': # Down
                    idx = (idx + 1) % len(sources)
        else:
            # Unix
            if ch == b'\n' or ch == b'\r':
                return [i for i, s in enumerate(selected) if s]
            if ch == b' ':
                selected[idx] = not selected[idx]
            if ch == b'\x1b':
                # read two more
                rest = sys.stdin.read(2)
                if rest == '[A':
                    idx = (idx - 1) % len(sources)
                elif rest == '[B':
                    idx = (idx + 1) % len(sources)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), "data")
    os.makedirs(data_dir, exist_ok=True)

    sources_file = os.path.join(script_dir, "sources.json")
    if not os.path.exists(sources_file):
        print(f"Sources file {sources_file} not found.")
        return

    with open(sources_file, "r") as f:
        sources = json.load(f)

    # CLI arg handling: if called with 'all', process all sources
    selected_sources = []
    if len(sys.argv) > 1:
        args = [a.lower() for a in sys.argv[1:]]
        if 'all' in args:
            selected_sources = sources
        else:
            for source in sources:
                name = source.get('name', source['type']).lower()
                if name in args:
                    selected_sources.append(source)

    if not selected_sources:
        # Multi-selection menu
        indices = interactive_selection(sources, title="Select source(s) to parse (Space to toggle, Enter to confirm)")
        if not indices:
            print("No selection made. Exiting.")
            return
        selected_sources = [sources[i] for i in indices]

    # Identify unique types and their selected URLs
    sources_by_type = {}
    for s in selected_sources:
        t = s['type']
        if t not in sources_by_type:
            sources_by_type[t] = []
        sources_by_type[t].append(s['url'])

    for source_type, urls in sources_by_type.items():
        process_csv(source_type, data_dir, selected_urls=urls)

if __name__ == "__main__":
    main()
