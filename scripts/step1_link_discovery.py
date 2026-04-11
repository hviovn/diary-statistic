import json
import urllib.request
import urllib.parse
import re
from datetime import datetime, timezone
import os
import yaml
import sys
import html

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
LINKS_DIR = os.path.join(DATA_DIR, 'step1_links')

def fetch_url(url):
    try:
        # Handle non-ASCII characters in URL
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.quote(parsed.path)
        url = urllib.parse.urlunparse(parsed._replace(path=path))

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
                    'url': post['link'],
                    'date': post['date'].split('T')[0],
                    'title': post['title']['rendered']
                })
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

                    if not created_date:
                        date_match = re.search(r'(\d{4})[/-](\d{2})[/-](\d{2})', slug)
                        if date_match:
                            created_date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
                        else:
                            date_match = re.search(r'(\d{4})[/-](\d{2})', slug)
                            if date_match:
                                created_date = f"{date_match.group(1)}-{date_match.group(2)}-01"
                            else:
                                date_match = re.search(r'\b(\d{4})\b', slug)
                                if date_match:
                                    created_date = f"{date_match.group(1)}-01-01"

                    if not created_date:
                        c = item.get('content', '')
                        date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', c)
                        if date_match:
                            created_date = date_match.group(1)

                    if not created_date and 'filePath' in item:
                        date_match = re.search(r'(\d{4})[/-](\d{2})[/-](\d{2})', item['filePath'])
                        if date_match:
                            created_date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"

                    if created_date:
                        created_date = created_date.split('T')[0]
                        link = f"{base_url}/{slug.lstrip('/')}"
                        link = link.replace('https://https://', 'https://')
                        posts.append({
                            'url': link,
                            'date': created_date,
                            'title': title
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
                        if not any(p['url'] == link for p in posts):
                            posts.append({
                                'url': link,
                                'date': date_str,
                                'title': title
                            })
                except Exception as e:
                    print(f"Error parsing RSS item: {e}")
    return posts

def fetch_github(username, exclude_repos=None, exclude_forks=False):
    import time
    print(f"Fetching GitHub data for user: {username}...")
    token = os.environ.get('GITHUB_TOKEN')
    headers = {'User-Agent': 'Mozilla/5.0'}
    if token:
        headers['Authorization'] = f'token {token}'

    def request_json(url):
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8')), resp

    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
        try:
            data, resp = request_json(url)
            if not data: break
            repos.extend(data)
            if len(data) < 100: break
            page += 1
        except Exception: break

    if exclude_forks or exclude_repos:
        repos = [r for r in repos if not (exclude_forks and r.get('fork')) and r.get('name') not in (exclude_repos or [])]

    all_entries = []
    for repo in repos:
        repo_name = repo['full_name']
        print(f"  Fetching commits for {repo_name}...")
        page = 1
        while True:
            url = f"https://api.github.com/repos/{repo_name}/commits?author={username}&per_page=100&page={page}"
            try:
                items, resp = request_json(url)
                if not items: break
                for item in items:
                    all_entries.append({
                        'url': item['html_url'],
                        'date': item['commit']['author']['date'].split('T')[0],
                        'title': f"[{repo_name}] {item['commit']['message'].split('\\n')[0]}",
                        'github_type': 'commit'
                    })
                if len(items) < 100: break
                page += 1
            except Exception: break

        # README
        default_branch = repo.get('default_branch', 'main')
        all_entries.append({
            'url': f"https://github.com/{repo_name}/blob/{default_branch}/README.md",
            'date': repo.get('pushed_at', '')[:10],
            'title': f"[{repo_name}] README.md",
            'github_type': 'readme'
        })
    return all_entries

def fetch_legacy_html(base_url, exclude_paths=None):
    print(f"Fetching Legacy HTML: {base_url}...")
    base_url = base_url.rstrip('/') + '/'
    to_visit = [base_url]
    visited = set()
    posts = []
    seen_links = set()
    date_patterns = [
        (r'\b(\d{4}-\d{2}-\d{2})\b', '%Y-%m-%d'),
        (r'\b(\d{2}\.\d{2}\.\d{4})\b', '%d.%m.%Y'),
    ]

    while to_visit and len(visited) < 800:
        url = to_visit.pop(0).split('#')[0]
        if url in visited: continue
        if exclude_paths and any(url.startswith(ex) for ex in exclude_paths): continue
        visited.add(url)

        content = fetch_url(url)
        if not content: continue

        found_date = None
        for pattern, fmt in date_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    found_date = datetime.strptime(match.group(1), fmt).strftime('%Y-%m-%d')
                    break
                except: continue

        title_match = re.search(r'<title>(.*?)</title>', content, re.I | re.S)
        title = html.unescape(re.sub('<[^<]+?>', '', title_match.group(1)).strip()) if title_match else url.split('/')[-1]

        if found_date and not url.endswith(('index.html', 'navigator.html')):
            if url.lower().rstrip('/') not in seen_links:
                seen_links.add(url.lower().rstrip('/'))
                posts.append({'url': url, 'date': found_date, 'title': title})

        links = re.findall(r'href=["\'](.*?)["\']', content)
        for link in links:
            abs_link = urllib.parse.urljoin(url, link).split('#')[0]
            if abs_link.startswith(base_url) and abs_link not in visited:
                if not abs_link.lower().endswith(('.jpg', '.png', '.pdf', '.zip', '.css', '.js')):
                    to_visit.append(abs_link)
    return posts

def main():
    with open(os.path.join(DATA_DIR, 'sources.yaml'), 'r') as f:
        sources = yaml.safe_load(f)

    os.makedirs(LINKS_DIR, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    for source in sources:
        sid = source['id']
        stype = source['type']
        surl = source['url']
        print(f"\nProcessing {sid} ({stype})...")

        history_file = os.path.join(LINKS_DIR, f"{sid}.json")
        existing_pages = {}
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                old_data = json.load(f)
                existing_pages = {p['url']: p for p in old_data.get('pages', [])}

        new_links = []
        if stype == 'wordpress':
            new_links = fetch_wordpress(surl)
        elif stype == 'quartz':
            new_links = fetch_quartz(surl)
        elif stype == 'github':
            new_links = fetch_github(surl, exclude_repos=source.get('exclude'), exclude_forks=source.get('exclude_forks'))
        elif stype == 'legacy_html':
            new_links = fetch_legacy_html(surl, exclude_paths=source.get('exclude'))

        pages = []
        for link in new_links:
            url = link['url']
            old_p = existing_pages.get(url)

            # Simple change detection for link discovery: title or date changed
            changed = True
            if old_p:
                if old_p.get('title') == link['title'] and old_p.get('date') == link['date']:
                    changed = False

            pages.append({
                'url': url,
                'title': link['title'],
                'date': link['date'],
                'last_seen': now,
                'changed': changed,
                'github_type': link.get('github_type') # preserved for github
            })

        output = {
            "source_id": sid,
            "type": stype,
            "base_url": surl,
            "last_checked": now,
            "pages": pages
        }

        with open(history_file, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"Saved {len(pages)} links for {sid}")

if __name__ == "__main__":
    main()
