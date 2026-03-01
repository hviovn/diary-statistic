import json
import urllib.request
import re
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

def strip_html(text):
    if not text:
        return ""
    # Remove script and style tags and their content
    text = re.sub(r'<(script|style).*?>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove other HTML tags
    text = re.sub('<[^<]+?>', '', text)
    # Unescape common entities
    text = html.unescape(text)
    return text

def fetch_wordpress_content(link):
    # For wordpress, the content might be easier to get via the API if we had the ID,
    # but we can also just fetch the page and try to extract it, or use the link which might be a REST URL or a web page.
    # Given the previous script, 'link' is the web page.
    # However, to be efficient, we could have saved the content in the first step.
    # But the instructions said: "Each of these contain a link to a source, a date, a title and the type."
    # AND "The second script... will then parse the four generated csv files... Each of these also contain the link and date, but the next column is the cleaned up text."
    # So I must fetch it here.
    content = fetch_url(link)
    return strip_html(content)

def fetch_github_content(link, source_type):
    if source_type == 'github commit':
        # For a commit link like https://github.com/user/repo/commit/hash
        # We can try to get the raw patch or just the commit message.
        # The original script used the API to get the message.
        # Since we only have the link now, we can try to use the API if we can parse the link.
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
                    data = json.loads(response.read().decode('utf-8'))
                    return data['commit']['message']
            except Exception as e:
                print(f"Error fetching github commit content: {e}")
    elif source_type == 'github readme':
        # For a readme link like https://github.com/user/repo/blob/branch/README.md
        # We can convert it to raw.githubusercontent.com
        raw_link = link.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
        return fetch_url(raw_link)

    return ""

def process_csv(source_type):
    os.makedirs('data', exist_ok=True)
    input_file = os.path.join('data', f"sources_{source_type}.csv")
    output_file = os.path.join('data', f"content_{source_type}.csv")

    if not os.path.exists(input_file):
        print(f"Input file {input_file} not found.")
        return

    print(f"Processing {input_file}...")
    results = []
    with open(input_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            link = row['Link']
            date = row['Date']
            row_type = row['Type']

            print(f"  Fetching content for {link}...")
            content = ""
            if source_type == 'wordpress' or source_type == 'quartz' or source_type == 'legacy_html':
                content = fetch_url(link)
                content = strip_html(content)
            elif source_type == 'github':
                content = fetch_github_content(link, row_type)

            results.append({
                'Link': link,
                'Date': date,
                'Cleaned Text': content
            })

    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Link', 'Date', 'Cleaned Text']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    print(f"Saved to {output_file}")

def main():
    sources = ['wordpress', 'quartz', 'legacy_html', 'github']
    for source in sources:
        process_csv(source)

if __name__ == "__main__":
    main()
