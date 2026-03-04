import json
import urllib.request
import csv
import os
import sys
import time
import re

def request_json(url, token=None, max_rate_wait=3600):
    headers = {'User-Agent': 'Mozilla/5.0'}
    if token:
        headers['Authorization'] = f'token {token}'

    attempts = 0
    while True:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                text = resp.read().decode('utf-8', errors='ignore')
                return json.loads(text), resp.info()
        except urllib.error.HTTPError as e:
            remaining = int(e.headers.get('X-RateLimit-Remaining') or -1)
            reset = int(e.headers.get('X-RateLimit-Reset') or 0)

            if (e.code in (403, 429)) and remaining <= 0 and reset:
                wait = max(0, reset - int(time.time())) + 1
                if wait > max_rate_wait:
                    print(f"Rate limit hit. Wait time {wait}s exceeds max_rate_wait.")
                    raise
                attempts += 1
                print(f"Rate limit hit. Sleeping {wait}s (attempt {attempts}) before retrying {url}")
                time.sleep(wait)
                continue
            else:
                raise
        except Exception:
            raise

def get_first_commit_date(owner, repo, token=None):
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"
    try:
        _, info = request_json(url, token)
        link_header = info.get('Link', '')
        # rel="last"
        match = re.search(r'<([^>]+)>;\s*rel="last"', link_header)
        if match:
            last_page_url = match.group(1)
            commits, _ = request_json(last_page_url, token)
            if commits:
                return commits[-1]['commit']['author']['date'].split('T')[0]
        else:
            # If no last link, it might be only one page
            commits, _ = request_json(url, token)
            if commits:
                return commits[-1]['commit']['author']['date'].split('T')[0]
    except Exception as e:
        print(f"Error fetching first commit for {owner}/{repo}: {e}")
    return "Unknown"

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/helper/create_repository_líst.py <username>")
        sys.exit(1)

    username = sys.argv[1]
    token = os.environ.get('GITHUB_TOKEN')

    print(f"Fetching repositories for user: {username}...")

    all_repos = []
    page = 1
    per_page = 100

    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page={per_page}&page={page}"
        try:
            repos, info = request_json(url, token)
            if not repos:
                break
            all_repos.extend(repos)
            if len(repos) < per_page:
                break
            page += 1
        except Exception as e:
            print(f"Error fetching repos for {username}: {e}")
            break

    results = []
    for repo in all_repos:
        repo_name = repo['name']
        full_name = repo['full_name']
        owner = repo['owner']['login']
        is_fork = repo['fork']
        has_pages = repo.get('has_pages', False)

        print(f"Processing {full_name}...")
        first_commit_date = get_first_commit_date(owner, repo_name, token)

        results.append({
            'Repository Name': repo_name,
            'First Commit Date': first_commit_date,
            'Is Fork': is_fork,
            'Has github.io website': has_pages
        })

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, f"list_repositories_{username}.csv")

    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Repository Name', 'First Commit Date', 'Is Fork', 'Has github.io website']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(f"Saved {len(results)} repositories to {output_file}")

if __name__ == "__main__":
    main()
