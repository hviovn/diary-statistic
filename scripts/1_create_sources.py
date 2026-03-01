import json
import urllib.request
import urllib.parse
import re
from datetime import datetime, date, timedelta
import os
import csv
import html

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
    print(f"Fetching GitHub data for user: {username}...")
    all_entries = []
    repos = {} # name -> latest_date
    per_page = 100
    current_year = date.today().year

    token = os.environ.get('GITHUB_TOKEN')

    # Fetch commits
    for year in range(current_year, 2010, -1):
        print(f"  Fetching commits for year {year}...")
        page = 1
        while page <= 10:
            query = f"author:{username} committer-date:{year}-01-01..{year}-12-31"
            url = f"https://api.github.com/search/commits?q={urllib.parse.quote(query)}&sort=committer-date&order=desc&page={page}&per_page={per_page}"
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/vnd.github.cloak-preview'
            }
            if token:
                headers['Authorization'] = f'token {token}'
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

                        all_entries.append({
                            'link': item['html_url'],
                            'date': commit_date,
                            'title': f"[{repo_name}] {msg}",
                            'type': 'github commit'
                        })

                        if repo_name not in repos or commit_date > repos[repo_name]:
                            repos[repo_name] = commit_date

                    if len(data['items']) < per_page:
                        break
                    page += 1
            except Exception as e:
                print(f"Error fetching GitHub commits for {year} page {page}: {e}")
                break

    # Add README entries for each repo
    for repo_name, last_date in repos.items():
        # We need the default branch to construct the link to README.md in the root
        # Or we can just use the repo URL + /blob/main/README.md as a guess,
        # but let's try to get it properly if we can.
        # To keep it simple and follow "link to the latest README.md in the root file"
        # I'll use the API to get the repository information
        print(f"  Fetching README info for {repo_name}...")
        repo_url = f"https://api.github.com/repos/{repo_name}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        if token:
            headers['Authorization'] = f'token {token}'
        try:
            req = urllib.request.Request(repo_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                repo_data = json.loads(response.read().decode('utf-8'))
                default_branch = repo_data.get('default_branch', 'main')
                readme_link = f"https://github.com/{repo_name}/blob/{default_branch}/README.md"
                all_entries.append({
                    'link': readme_link,
                    'date': last_date,
                    'title': f"[{repo_name}] README.md",
                    'type': 'github readme'
                })
        except Exception as e:
            print(f"  Error fetching repo info for {repo_name}: {e}")
            # Fallback
            all_entries.append({
                'link': f"https://github.com/{repo_name}/blob/main/README.md",
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
                if not abs_link.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.doc', '.css', '.js')):
                    to_visit.append(abs_link)

    return posts

def save_to_csv(data, filename):
    os.makedirs('../data', exist_ok=True)
    filepath = os.path.join('../data', filename)
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
    data_dir = os.path.join(os.path.dirname(script_dir), "../data")
    os.makedirs(data_dir, exist_ok=True)

    sources_file = os.path.join(script_dir, "sources.json")
    with open(sources_file, "r") as f:
        sources = json.load(f)

    for source in sources:
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

        save_to_csv(data, f"sources_{type_name}.csv", data_dir)

if __name__ == "__main__":
    main()
