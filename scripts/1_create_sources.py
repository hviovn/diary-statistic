import json
import urllib.request
import urllib.parse
import re
from datetime import datetime, date, timedelta
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

def fetch_url(url):
    try:
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
                    'link': post['link'],
                    'date': post['date'].split('T')[0],
                    'title': post['title']['rendered'],
                    'type': 'wordpress'
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
                            'link': link,
                            'date': created_date,
                            'title': title,
                            'type': 'quartz'
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
                                'link': link,
                                'date': date_str,
                                'title': title,
                                'type': 'quartz'
                            })
                except Exception as e:
                    print(f"Error parsing RSS item: {e}")
    return posts

def fetch_github(username):
    import time

    print(f"Fetching GitHub data for user: {username} (per-repo mode)...")
    token = os.environ.get('GITHUB_TOKEN')
    headers = {'User-Agent': 'Mozilla/5.0'}
    if token:
        headers['Authorization'] = f'token {token}'

    def request_json(url, accept_header=None):
        req_headers = dict(headers)
        if accept_header:
            req_headers['Accept'] = accept_header
        req = urllib.request.Request(url, headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                text = resp.read().decode('utf-8', errors='ignore')
                return json.loads(text), resp
        except Exception as e:
            raise

    # 1) List repos for the user (paginated)
    repos = []
    page = 1
    per_page = 100
    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page={per_page}&page={page}"
        try:
            data, resp = request_json(url)
        except Exception as e:
            print(f"Error listing repos for {username}: {e}")
            break
        if not data:
            break
        repos.extend(data)
        if len(data) < per_page:
            break
        page += 1
        try:
            remaining = int(resp.getheader('X-RateLimit-Remaining') or 0)
            reset = int(resp.getheader('X-RateLimit-Reset') or 0)
            if remaining <= 1:
                wait = max(0, reset - int(time.time())) + 1
                print(f"Rate limit reached, sleeping {wait}s")
                time.sleep(wait)
        except Exception:
            pass

    all_entries = []
    repos_latest = {}

    # 2) For each repo, list commits by the user
    for repo in repos:
        repo_name = repo.get('full_name')
        if not repo_name:
            continue
        print(f"  Fetching commits for repo: {repo_name}...")
        page = 1
        while True:
            commits_url = (f"https://api.github.com/repos/{repo_name}/commits"
                           f"?author={urllib.parse.quote(username)}&per_page={per_page}&page={page}")
            try:
                items, resp = request_json(commits_url)
            except Exception as e:
                print(f"    Error fetching commits for {repo_name} page {page}: {e}")
                break
            if not items:
                break
            for item in items:
                try:
                    commit_date = item['commit']['author']['date'].split('T')[0]
                    msg = item['commit']['message'].split('\n')[0]
                    all_entries.append({
                        'link': item.get('html_url'),
                        'date': commit_date,
                        'title': f"[{repo_name}] {msg}",
                        'type': 'github commit'
                    })
                    if repo_name not in repos_latest or commit_date > repos_latest[repo_name]:
                        repos_latest[repo_name] = commit_date
                except Exception:
                    continue

            if len(items) < per_page:
                break
            page += 1

            try:
                remaining = int(resp.getheader('X-RateLimit-Remaining') or 0)
                reset = int(resp.getheader('X-RateLimit-Reset') or 0)
                if remaining <= 1:
                    wait = max(0, reset - int(time.time())) + 1
                    print(f"Rate limit reached, sleeping {wait}s")
                    time.sleep(wait)
            except Exception:
                pass

    # 3) Add README links for each repo using repo info from listing
    for repo in repos:
        repo_name = repo.get('full_name')
        if not repo_name:
            continue
        last_date = repos_latest.get(repo_name, repo.get('pushed_at', '')[:10] if repo.get('pushed_at') else '')
        default_branch = repo.get('default_branch', 'main')
        readme_link = f"https://github.com/{repo_name}/blob/{default_branch}/README.md"
        all_entries.append({
            'link': readme_link,
            'date': last_date,
            'title': f"[{repo_name}] README.md",
            'type': 'github readme'
        })

    return all_entries

def fetch_legacy_html(base_url):
    print(f"Fetching Legacy HTML: {base_url}...")
    base_url = base_url.rstrip('/') + '/'
    to_visit = [base_url]
    visited = set()
    posts = []
    seen_links = set()

    # Only allow these text-like extensions; directories (paths ending with '/') are allowed
    allowed_text_exts = {'.html', '.htm', '.txt', '.md'}
    # Explicit blacklist for common non-text/code/binary extensions
    blacklist_exts = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.doc', '.docx', '.exe', '.class', '.java', '.cpp', '.bin', '.o', '.so', '.dll', '.jar', '.tar', '.gz'}

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
        title = html.unescape(title)

        if found_date_str and not url_no_frag.endswith(('index.html', 'navigator.html', 'rechts.html')):
            # normalize and filter by extension to include only text files
            parsed = urllib.parse.urlparse(url_no_frag)
            path = parsed.path or ''
            if path.endswith('/'):
                allow_post = True
            else:
                ext = os.path.splitext(path)[1].lower()
                if not ext:
                    allow_post = False
                elif ext in blacklist_exts:
                    allow_post = False
                else:
                    allow_post = ext in allowed_text_exts

            if allow_post:
                norm = url_no_frag.rstrip('/').lower()
                if norm not in seen_links:
                    seen_links.add(norm)
                    posts.append({
                        'link': url_no_frag,
                        'date': found_date_str,
                        'title': title,
                        'type': 'legacy_html'
                    })

        links = re.findall(r'href=["\'](.*?)["\']', content)
        for link in links:
            abs_link = urllib.parse.urljoin(url_no_frag, link).split('#')[0]
            if abs_link.startswith(base_url) and abs_link not in visited:
                # continue crawling directories and HTML-like pages; skip common binary/media files
                lower = abs_link.lower()
                if not lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.doc', '.css', '.js', '.exe', '.class', '.java', '.cpp', '.bin', '.o', '.so', '.dll')):
                    to_visit.append(abs_link)

    return posts

def save_to_csv(data, filename):
    # Delegate to save_to_csv_with_dir with the repo-root data directory
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    save_to_csv_with_dir(data, filename, data_dir)


def save_to_csv_with_dir(data, filename, data_dir=None):
    if not data_dir:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    os.makedirs(data_dir, exist_ok=True)
    filepath = os.path.join(data_dir, filename)
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Link', 'Date', 'Title', 'Type']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for item in data:
            writer.writerow({
                'Link': item['link'],
                'Date': item['date'],
                'Title': item['title'],
                'Type': item['type']
            })
    print(f"Saved {len(data)} entries to {filepath}")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # place data directory at the repository root (same level as `scripts`)
    data_dir = os.path.join(os.path.dirname(script_dir), "data")
    os.makedirs(data_dir, exist_ok=True)

    sources_file = os.path.join(script_dir, "sources.json")
    with open(sources_file, "r") as f:
        sources = json.load(f)

    # CLI arg handling: if called with 'all', process all sources
    selected_sources = []
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'all':
        selected_sources = sources
    else:
        # Build menu items
        menu_items = [f"{s.get('type')} - {s.get('url')}" for s in sources]
        sel = interactive_menu(menu_items, title="Select a source to fetch (Enter to confirm)")
        if sel is None:
            print("No selection made. Exiting.")
            return
        selected_sources = [sources[sel]]

    for source in selected_sources:
        type_name = source['type']
        data = []
        if type_name == 'wordpress':
            data = fetch_wordpress(source['url'])
        elif type_name == 'quartz':
            data = fetch_quartz(source['url'])
        elif type_name == 'legacy_html':
            data = fetch_legacy_html(source['url'])
        elif type_name == 'github':
            data = fetch_github(source['url'])

        save_to_csv_with_dir(data, f"sources_{type_name}.csv", data_dir)


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


def interactive_menu(options, title=None):
    idx = 0
    while True:
        # clear screen
        if os.name == 'nt':
            os.system('cls')
        else:
            os.system('clear')

        if title:
            print(title)
        print('Use Up/Down arrows and Enter to select. Ctrl-C to cancel.')
        for i, opt in enumerate(options):
            prefix = '=> ' if i == idx else '   '
            print(f"{prefix}{opt}")

        try:
            ch = _getch()
        except Exception:
            print('\nInput error; falling back to numeric selection.')
            for i, opt in enumerate(options):
                print(f"{i+1}. {opt}")
            try:
                choice = int(input('Enter number: ')) - 1
                if 0 <= choice < len(options):
                    return choice
            except Exception:
                return None

        # Windows msvcrt returns b'\r' for Enter, arrow keys are two-byte sequences
        if msvcrt:
            if ch in (b'\r', b'\n'):
                return idx
            if ch in (b'\x00', b'\xe0'):
                ch2 = msvcrt.getch()
                if ch2 == b'H':
                    idx = (idx - 1) % len(options)
                elif ch2 == b'P':
                    idx = (idx + 1) % len(options)
        else:
            # Unix: arrow sequences start with ESC (27)
            if ch == b'\n' or ch == b'\r':
                return idx
            if ch == b'\x1b':
                # read two more
                rest = sys.stdin.read(2)
                if rest == '[A':
                    idx = (idx - 1) % len(options)
                elif rest == '[B':
                    idx = (idx + 1) % len(options)

if __name__ == "__main__":
    main()
