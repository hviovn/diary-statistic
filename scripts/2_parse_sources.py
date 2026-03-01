import json
import urllib.request
import re
import os
import csv
import html
import sys

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

def process_csv(source_type, data_dir):
    """Read sources CSV and generate content CSV."""
    input_file = os.path.join(data_dir, f"sources_{source_type}.csv")
    output_file = os.path.join(data_dir, f"content_{source_type}.csv")

    if not os.path.exists(input_file):
        print(f"Input file {input_file} not found.")
        return

    print(f"Processing {input_file}...")
    results = []
    with open(input_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            link = row['Link']
            row_type = row['Type']

            print(f"  Fetching content for {link}...")
            content = ""
            if source_type in ['wordpress', 'quartz', 'legacy_html']:
                raw_content = fetch_url(link)
                content = strip_html(raw_content)
            elif source_type == 'github':
                content = fetch_github_content(link, row_type)

            results.append({
                'link': link,
                'content': content
            })

    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['link', 'content']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    print(f"Saved to {output_file}")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), "data")
    os.makedirs(data_dir, exist_ok=True)

    sources = ['wordpress', 'quartz', 'legacy_html', 'github']
    for source in sources:
        process_csv(source, data_dir)

if __name__ == "__main__":
    main()
