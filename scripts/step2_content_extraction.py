import json
import urllib.request
import re
import os
import html
import hashlib
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
LINKS_DIR = os.path.join(DATA_DIR, 'step1_links')
CONTENT_DIR = os.path.join(DATA_DIR, 'step2_content')

def fetch_url_with_headers(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
            return {
                'content': content,
                'last_modified': resp.headers.get('Last-Modified'),
                'etag': resp.headers.get('ETag')
            }
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def strip_html(text):
    if not text: return ""
    text = re.sub(r'<(script|style).*?>.*?</\1>', ' ', text, flags=re.DOTALL | re.I)
    text = re.sub('<[^<]+?>', ' ', text)
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()

def get_hash(content):
    return hashlib.sha256(content).hexdigest()

def main():
    if not os.path.exists(LINKS_DIR):
        print("Link discovery (Step 1) not found.")
        return

    os.makedirs(CONTENT_DIR, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    for filename in os.listdir(LINKS_DIR):
        if not filename.endswith('.json'): continue

        with open(os.path.join(LINKS_DIR, filename), 'r') as f:
            link_data = json.load(f)

        sid = link_data['source_id']
        stype = link_data['type']
        print(f"\nProcessing content for {sid}...")

        source_content_dir = os.path.join(CONTENT_DIR, sid)
        if stype != 'github':
            os.makedirs(source_content_dir, exist_ok=True)

        github_entries_map = {}
        if stype == 'github':
            github_path = os.path.join(CONTENT_DIR, f"{sid}.json")
            if os.path.exists(github_path):
                with open(github_path, 'r') as f:
                    old_github_entries = json.load(f)
                    github_entries_map = {e['url']: e for e in old_github_entries}

        github_entries = []

        for page in link_data['pages']:
            url = page['url']

            # Load existing content for change detection
            old_content = None
            if stype == 'github':
                old_content = github_entries_map.get(url)
            else:
                page_filename = hashlib.md5(url.encode()).hexdigest() + ".json"
                page_path = os.path.join(source_content_dir, page_filename)
                if os.path.exists(page_path):
                    with open(page_path, 'r') as f:
                        old_content = json.load(f)

            if not page['changed'] and old_content:
                print(f"  Skipping {url} (unchanged)")
                if stype == 'github': github_entries.append(old_content)
                continue

            print(f"  Fetching/Processing {url}...")

            if stype == 'github' and page.get('github_type') == 'commit':
                # Use title for commit message to avoid rate limits
                text = re.sub(r'^\[.*?\]\s*', '', page['title'])
                entry = {
                    'url': url,
                    'fetched_at': now,
                    'text': text,
                    'images': [],
                    'files': []
                }
                github_entries.append(entry)
                continue

            # Fetch actual content for others
            fetch_result = fetch_url_with_headers(url)
            if not fetch_result:
                if old_content:
                    print(f"    Failed to fetch {url}, using old content.")
                    if stype == 'github': github_entries.append(old_content)
                continue

            raw_text = fetch_result['content'].decode('utf-8', errors='ignore')
            clean_text = strip_html(raw_text)
            content_hash = get_hash(fetch_result['content'])

            if old_content and old_content.get('hash') == content_hash:
                print(f"    Content hash identical for {url}")
                if stype == 'github': github_entries.append(old_content)
                continue

            entry = {
                'url': url,
                'fetched_at': now,
                'last_modified': fetch_result['last_modified'],
                'etag': fetch_result['etag'],
                'hash': content_hash,
                'text': clean_text,
                'images': [],
                'files': []
            }

            if stype == 'github':
                github_entries.append(entry)
            else:
                page_filename = hashlib.md5(url.encode()).hexdigest() + ".json"
                page_path = os.path.join(source_content_dir, page_filename)
                with open(page_path, 'w') as f:
                    json.dump(entry, f, indent=2)

        if stype == 'github':
            github_path = os.path.join(CONTENT_DIR, f"{sid}.json")
            with open(github_path, 'w') as f:
                json.dump(github_entries, f, indent=2)

if __name__ == "__main__":
    main()
